import net.layers.application
import coding.message
import pickle
import struct
import threading
import time
import random


class DelugePDU(object):
    # B: unsigned char
    # 1 - ADV
    # 2 - REQ
    # 3 - DATA
    HEADER_PREFIX = "B"
    HEADER_PREFIX_SIZE = struct.calcsize(HEADER_PREFIX)

    # I: unsigned int
    # version, page_number, packet_number
    DATA_HEADER = "III"
    DATA_HEADER_SIZE = struct.calcsize(DATA_HEADER)

    ADV = 0
    REQ = 1
    DATA = 2

    def __init__(self, msg_type, message):
        self.msg_type = msg_type
        self.message = message

        if self.is_adv():
            self.version, self.largest_completed_page = \
                pickle.loads(self.message)
        elif self.is_req():
            self.version, self.page_number, self.packets = \
                pickle.loads(self.message)
        elif self.is_data():
            self.version, self.page_number, self.packet_number = \
                struct.unpack(self.DATA_HEADER, self.message[:self.DATA_HEADER_SIZE])
            self.data = self.message[self.DATA_HEADER_SIZE:]

    @property
    def type(self):
        if self.is_adv():
            return 'ADV'
        elif self.is_req():
            return 'REQ'
        elif self.is_data():
            return 'DATA'

    def is_adv(self):
        return self.msg_type == self.ADV

    def is_req(self):
        return self.msg_type == self.REQ

    def is_data(self):
        return self.msg_type == self.DATA

    def to_string(self):
        header = struct.pack(self.HEADER_PREFIX, self.msg_type)
        return header + self.message

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_PREFIX, data[:cls.HEADER_PREFIX_SIZE])
        return cls(x[0], data[cls.HEADER_PREFIX_SIZE:])

    @classmethod
    def create_data_packet(cls, version, page_number, packet_number, data):
        header = struct.pack(cls.DATA_HEADER, version, page_number, packet_number)
        return cls(cls.DATA, header + data)

    @classmethod
    def create_adv_packet(cls, version, largest_completed_page):
        message = pickle.dumps([version, largest_completed_page])
        return cls(cls.ADV, message)

    @classmethod
    def create_req_packet(cls, version, page_number, packets):
        message = pickle.dumps([version, page_number, packets])
        return cls(cls.REQ, message)


class DelugeState(object):
    """Enum of the states of the Deluge Protocol."""
    MAINTAIN = 'MAINTAIN'
    RX = 'RX'
    TX = 'TX'


class Deluge(net.layers.application.Application):
    PORT = 11
    PAGE_SIZE = 1000
    PACKET_SIZE = 100
    PACKETS_PER_PAGE = 10

    # Bounds for the length of each round.
    T_MIN = .1
    T_MAX = 20

    # Threshold of overheard packets for message suppression.
    K = 1

    def get_port(self):
        return self.PORT

    def new_version(self, version, data):
        # Only update if the version is later than the current version.
        if version <= self.version:
            return

        self.version = version
        self.complete_pages = []
        self.buffering_pages = {}
        self._split_data_into_pages_and_packets(data)

    def _split_data_into_pages_and_packets(self, data):
        # TMP: Handle padding of variable length data.
        if (len(data) % self.PAGE_SIZE) != 0:
            padding = (len(data) + self.PAGE_SIZE)
            padding -= padding % self.PAGE_SIZE
            data += 'x' * (padding - len(data))

        current_index = 0
        page_number = 0
        while current_index < len(data):
            page_end = current_index + self.PAGE_SIZE
            packets = {}
            packet_number = 0
            while current_index < page_end and current_index < len(data):
                packet_end = current_index + self.PACKET_SIZE
                packets[packet_number] = data[current_index:packet_end]
                packet_number += 1
                current_index += self.PACKET_SIZE
            self.complete_pages.append(packets)
            page_number += 1

    def __init__(self):
        super(Deluge, self).__init__()

        # The current version
        self.version = 0

        # Page/Packet information.
        self.complete_pages = []
        self.buffering_pages = {}

        # The state of the protocols. Starts in the MAINTAIN state.
        self.state = DelugeState.MAINTAIN

        # The length of the window. This is dynamically adjusted to be between
        # T_MIN and T_MAX to allow for fast propagation of new versions and low
        # maintainance overhead.
        self.t = self.T_MIN

        # Number of ADV overheard with similar summaries.
        self.adv_overheard = 0

        # REQ for pages overheard
        self.req_overheard = set()

        # DATA received/overheard
        self.data_overheard = set()

        # Whether network is inconsistent based on the packets heard during the
        # current round.
        self.inconsistent = False

        # A buffer of DATA (page, packet) tuples to send.
        self._pending_datas = set()

        # A buffer of REQ, page numbers and packets, to send. We remove from
        # this if we overhear a similar REQ (page, packets) or receive the
        # corresponding DATA packets
        self._pending_reqs = set()

        # Timers and threads
        self._send_adv_timer = None
        self._send_req_timer = None
        self._next_round_timer = None

    def start(self, *args, **kwargs):
        super(Deluge, self).start(*args, **kwargs)
        self._start_next_round()

    def _start_next_round(self, delay=0):
        if self._send_adv_timer is not None:
            self._send_adv_timer.cancel()
        if self._send_req_timer is not None:
            self._send_req_timer.cancel()
        if self._next_round_timer is not None:
            self._next_round_timer.cancel()

        self._next_round_timer = threading.Timer(delay, self._round)
        self._next_round_timer.start()

    def _round(self):
        # If no overheard packet indicates an inconsistency in the previous
        # round, update t
        self.t = self.T_MIN if self.inconsistent else min(self.t * 2, self.T_MAX)

        # Reset state variables.
        self.inconsistent = False
        self.adv_overheard = 0
        self.req_overheard = set()
        self.data_overheard = set()

        if self.state == DelugeState.MAINTAIN:
            self._start_next_round(delay=self.t)
            self._send_adv_delayed()
        elif self.state == DelugeState.RX:
            self.inconsistent = True
            self._start_next_round(delay=self.t)
            self._send_req_delayed()
        elif self.state == DelugeState.TX:
            self.inconsistent = True
            # Send DATA in round robin fashion.
            print self._pending_datas
            while len(self._pending_datas) != 0:
                page, packet = self._pending_datas.pop()
                self.send_data(page, packet)
                # time.sleep(self._get_random_t_tx())
            self.state = DelugeState.MAINTAIN
            self._start_next_round(delay=0)

    def process_incoming(self, data, metadata=None):
        data_unit = DelugePDU.from_string(data)
        self.log(data_unit, metadata)

        if data_unit.is_adv():
            self._process_adv(data_unit)
            return

        # REQ or DATA
        if self.version != data_unit.version:
            self.inconsistent = True
            # TODO: Broadcast updated object profile.
            if self.state == DelugeState.MAINTAIN:
                self._start_next_round(delay=0)

        if data_unit.is_req():
            self._process_req(data_unit)
        elif data_unit.is_data():
            self._process_data(data_unit)

    def _send_adv_delayed(self):
        # Wait for a random amount of time (between self.t / 2 and self.t)
        rand_t = self._get_random_t_adv()
        if self._send_adv_timer is not None:
            self._send_adv_timer.cancel()
        self._send_adv_timer = threading.Timer(rand_t, self._send_adv)
        self._send_adv_timer.start()

    def _send_adv(self):
        # Only send ADV if during the current window, we overhear less than K
        # summaries with similar (v, pages).
        if self.adv_overheard >= self.K:
            return
        # TMP: Don't pollute the logs with empty ADVs.
        if len(self.complete_pages) == 0:
            return
        adv = DelugePDU.create_adv_packet(self.version, len(self.complete_pages))
        self.send(adv.to_string())

    def _send_req_delayed(self):
        rand_t = self._get_random_t_req()
        if self._send_req_timer is not None:
            self._send_req_timer.cancel()
        self._send_req_timer = threading.Timer(rand_t, self._send_req)
        self._send_req_timer.start()

    def _send_req(self):
        if len(self.req_overheard) or len(self.data_overheard):
            return
        if len(self._pending_reqs) == 0:
            return
        page_to_req = min(self._pending_reqs)
        current_packets = set(self.buffering_pages[page_to_req].keys())
        missing_packets = set(xrange(self.PACKETS_PER_PAGE)) - current_packets
        req = DelugePDU.create_req_packet(self.version, page_to_req, missing_packets)
        self.send(req.to_string())

    def _process_adv(self, data_unit):
        # Check if network is consistent.
        if data_unit.version > self.version:
            self.version = data_unit.version
            self.buffering_pages = {}
            self.complete_pages = []
        
        if data_unit.largest_completed_page == len(self.complete_pages):
            self.adv_overheard += 1
            return

        if data_unit.largest_completed_page > len(self.complete_pages) and \
                self.state == DelugeState.MAINTAIN:
            # Queue the next page to be requested.
            page_to_req = len(self.complete_pages)
            self._pending_reqs.add(page_to_req)
            if page_to_req not in self.buffering_pages:
                self.buffering_pages[page_to_req] = {}
            self.state = DelugeState.RX

        # Summary from ADV differs, Immediately start the next round.
        self.inconsistent = True
        self._start_next_round(delay=0)

    def _process_req(self, data_unit):
        self.req_overheard.add(data_unit.page_number)

        # React to REQ, transit to TX state if we have the requested page.
        if data_unit.page_number < len(self.complete_pages) and \
                self.state != DelugeState.RX:
            self.state = DelugeState.TX
            for packet in data_unit.packets:
                self._pending_datas.add((data_unit.page_number, packet))
            self.inconsistent = True
            self._start_next_round(delay=0)

    def _process_data(self, data_unit):
        self.data_overheard.add((data_unit.page_number, data_unit.packet_number))

        # Store data if applicable.
        if data_unit.page_number >= len(self.complete_pages):
            if data_unit.page_number not in self.buffering_pages:
                self.buffering_pages[data_unit.page_number] = {}

            if data_unit.packet_number not in self.buffering_pages[data_unit.page_number]:
                self.buffering_pages[data_unit.page_number][data_unit.packet_number] = data_unit.message

        # If we complete the next page, move it (and all applicable pages) to
        # the completed pages.
        next_page = len(self.complete_pages)
        while next_page in self.buffering_pages and \
                len(self.buffering_pages[next_page]) == self.PACKETS_PER_PAGE:
            # Exit the RX state
            if self.state == DelugeState.RX:
                self.state = DelugeState.MAINTAIN
            self.complete_pages.append(self.buffering_pages[next_page])
            if next_page in self._pending_reqs:
                self._pending_reqs.remove(next_page)
            del self.buffering_pages[next_page]
            next_page += 1

    def send_data(self, page_number, packet_number):
        try:
            data = DelugePDU.create_data_packet(
                self.version, page_number, packet_number,
                self.complete_pages[page_number][packet_number])
            self.send(data.to_string())
        except KeyError, e:
            print str(e)

    def log(self, data_unit, metadata):
        # tmp. figure out something cleaner.
        if data_unit.is_adv():
            msg = "%s, %s" % (data_unit.version, data_unit.largest_completed_page)
        elif data_unit.is_req():
            msg = "%s, %s" % (data_unit.page_number, data_unit.packets)
        elif data_unit.is_data():
            msg = "%s, %s" % (data_unit.page_number, data_unit.packet_number)
        self.logger.debug("(%s, %s, %s, %s): Received: %s, %s From: %s" % \
            (self.addr, self.state, len(self.complete_pages), self.t,
                data_unit.type, msg, metadata.sender_addr))

    def _get_random_t_adv(self):
        return random.uniform(self.t / 2.0, self.t)

    def _get_random_t_req(self):
        return random.uniform(0, self.t / 2.0)

    def _get_random_t_tx(self):
        return random.uniform(0, self.T_MIN)