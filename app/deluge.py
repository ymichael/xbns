import net.layers.application
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

    ADV = 1
    REQ = 2
    DATA = 3

    def __init__(self, msg_type, message):
        self.msg_type = msg_type
        self.message = message

        if self.is_adv():
            self.version, self.pages, self.packets_per_page = \
                pickle.loads(self.message)
        elif self.is_req():
            self.version, self.page_number, self.packets = \
                pickle.loads(self.message)
        elif self.is_data():
            self.version, self.page_number, self.packet_number = \
                struct.unpack(self.DATA_HEADER, self.message[:self.DATA_HEADER_SIZE])
            self.data = self.message[self.DATA_HEADER_SIZE:]

    def get_msg_type(self):
        if self.is_adv():
            return "ADV"
        elif self.is_req():
            return "REQ"
        elif self.is_data():
            return "DATA"

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
    def create_adv_packet(cls, version, pages, packets_per_page):
        message = pickle.dumps([version, pages, packets_per_page])
        return cls(cls.ADV, message)

    @classmethod
    def create_req_packet(cls, version, page_number, packets):
        message = pickle.dumps([version, page_number, packets])
        return cls(cls.REQ, message)


class State(object):
    MAINTAIN = 'MAINTAIN'
    RX = 'RX'
    TX = 'TX'


class Deluge(net.layers.application.Application):
    PORT = 11
    PAGE_SIZE = 1000
    PACKET_SIZE = 100

    T_MIN = .1
    T_MAX = 5
    K = 1
    TX_T = .1

    def get_port(self):
        return self.PORT

    def new_version(self, version, data):
        # Only update if the version is later than the current version.
        if version <= self.version:
            return

        self.version = version
        self.complete_pages = {}
        self.packets_per_page =[]
        self.buffering_pages = {}
        self._split_data_into_pages_and_packets(data)

    def _split_data_into_pages_and_packets(self, data):
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
            self.complete_pages[page_number] = packets
            self.packets_per_page.append(len(packets))
            page_number += 1

    def __init__(self):
        super(Deluge, self).__init__()

        # The current version
        self.version = 0

        # The state of the protocols. Starts in the MAINTAIN state.
        self.state = State.MAINTAIN

        # The length of the window. This is dynamically adjusted to be between
        # T_MIN and T_MAX to allow for fast propagation of new versions and low
        # maintainance overhead.
        self.t = self.T_MIN

        # Number of ADV overheard that are similar to self during the current
        # window.
        self.k = 0

        # Whether network is inconsistent. This results when we overhear an ADV
        # that does not match our state (both ahead and behind).
        # This is reset per window and used to dynamically adjust the window
        # length.
        self.inconsistent = False

        # A buffer of DATA (page, packet) tuples to send. We remove from this
        # set if we overhear a similar DATA (page, packet).
        self._pending_datas = set()

        # A buffer of REQ, page numbers, to send. We remove from this
        # set if we overhear a similar REQ (page, packets).
        self._pending_reqs = set()

        # Page/Packet information.
        self.complete_pages = {}
        self.packets_per_page = []
        self.buffering_pages = {}

        # Timers and threads
        self._send_adv_timer = None
        self._next_round_timer = None

    def start(self, *args, **kwargs):
        super(Deluge, self).start(*args, **kwargs)

        # Start round.
        self._restart_round()

    def _round(self):
        if self.state == State.MAINTAIN:
            self._round_maintain()
        elif self.state == State.RX:
            self._round_rx()
        elif self.state == State.TX:
            self._round_tx()

        # Start timer for next round.
        self._next_round_timer.cancel()
        self._next_round_timer = threading.Timer(self.t, self._round)
        self._next_round_timer.start()

    def _round_maintain(self):
        # Reset k to 0
        self.k = 0

        # If no overhead packet indicates an inconsistency in the previous
        # round, update t
        if not self.inconsistent:
            self.t = min(self.t * 2, self.T_MAX)
        else:
            self.t = self.T_MIN
        self.inconsistent = False

        # Wait for a random amount of time (between self.t / 2 and self.t)
        rand_t = self._get_random_t_adv()
        self._send_adv_timer = threading.Timer(rand_t, self._send_adv)
        self._send_adv_timer.start()

    def _round_rx(self):
        rand_req_t = self._get_random_t_req()
        time.sleep(rand_req_t)
        if len(self._pending_reqs) != 0:
            req_page = self._pending_reqs.pop()
            all_packets_in_page = set(xrange(self.packets_per_page[req_page]))
            if req_page in self.buffering_pages:
                received_packets = self.buffering_pages[req_page].keys()
                missing_packets = all_packets_in_page - set(received_packets)
            else:
                missing_packets = all_packets_in_page
            self.send_req(req_page, missing_packets)

        # Go back to the MAINTAIN state.
        self.state = State.MAINTAIN

    def _round_tx(self):
        while len(self._pending_datas) != 0:
            rand_tx_t = self._get_random_t_tx()
            time.sleep(rand_tx_t)
            if len(self._pending_datas) != 0:
                page, packet = self._pending_datas.pop()
                self.send_data(page, packet)

        # Go back to the MAINTAIN state.
        self.state = State.MAINTAIN

    def _get_random_t_adv(self):
        return random.uniform(self.t / 2.0, self.t)

    def _get_random_t_req(self):
        return random.uniform(0, self.t / 2.0)

    def _get_random_t_tx(self):
        return random.uniform(0, self.TX_T)

    def _send_adv(self):
        # Only send ADV if during the current window, we overhear less than K
        # summaries with similar (v, pages).
        if self.k >= self.K:
            return

        # TMP:
        if len(self.complete_pages.keys()) == 0:
            return

        adv = DelugePDU.create_adv_packet(
            self.version, self.complete_pages.keys(), self.packets_per_page)
        self.send(adv.to_string())

    def _process_adv(self, data_unit):
        # Check if network is consistent.
        if data_unit.version > self.version:
            self.version = data_unit.version
            self.packets_per_page = data_unit.packets_per_page
            self.buffering_pages = {}
            self.complete_pages = {}

        adv_pages = set(data_unit.pages)
        own_pages = set(self.complete_pages.keys())

        # Increase k if ADV is same.
        if adv_pages == own_pages:
            self.k += 1
        else:
            missing_pages = adv_pages - own_pages
            should_request = len(missing_pages) != 0 or \
                    max(adv_pages) > max(own_pages)

            if self.state == State.MAINTAIN and should_request:
                self.state = State.RX

                # Queue the various packets to request.
                req_page = min(missing_pages)
                self._pending_reqs.add(req_page)

            # Set t to T_MIN and start new round.
            self.inconsistent = True
            self._restart_round(cancel_adv=should_request)

    def _restart_round(self, cancel_adv=False):
        if self._send_adv_timer is not None:
            self._send_adv_timer.cancel()
        if self._next_round_timer is not None:
            self._next_round_timer.cancel()

        self._next_round_timer = threading.Timer(0, self._round)
        self._next_round_timer.start()

    def process_incoming(self, data, metadata=None):
        data_unit = DelugePDU.from_string(data)
        self.log(data_unit, metadata)
        if data_unit.is_adv():
            self._process_adv(data_unit)
        elif data_unit.is_req():
            self._process_req(data_unit)
        elif data_unit.is_data():
            self._process_data(data_unit)

    def _process_req(self, data_unit):
        if self.version != data_unit.version:
            return

        # Remove similar REQ from pending buffer, so that we don't flood the
        # network with a similar, useless packet.
        if data_unit.page_number in self._pending_reqs:
            self._pending_reqs.remove(data_unit.page_number)

        # React to REQ, transit to TX state if we have the requested page.
        if self.state == State.MAINTAIN:
            if data_unit.page_number in self.complete_pages:
                self.state = State.TX

        # Add to data packets to queue.
        if self.state == State.MAINTAIN or self.state == State.TX:
            for packet in data_unit.packets:
                self._pending_datas.add((data_unit.page_number, packet))

        self.inconsistent = True

    def _process_data(self, data_unit):
        if self.version != data_unit.version:
            return

        # Remove similar DATA from pending buffer, so that we don't flood the
        # network with a similar, useless packet.
        # TODO: A more aggressive strategy would remove all DATA packets from
        # the same overheard page.
        page_no = data_unit.page_number
        packet_no = data_unit.packet_number
        data = (page_no, packet_no)
        if data in self._pending_datas:
            self._pending_datas.remove(data)

        # Store data if applicable.
        if page_no not in self.buffering_pages:
            self.buffering_pages[page_no] = {}
        if packet_no not in self.buffering_pages[page_no]:
            self.buffering_pages[page_no][packet_no] = data_unit.message

        # If we complete a page, move it to complete page.
        if len(self.buffering_pages[page_no]) == self.packets_per_page[page_no]:
            # If we are in the RX state, and the completed page is the page
            # that triggered entry into the RX state, transit to the MAINTAIN
            # state. (TODO).
            if self.state == State.RX:
                self.state = State.MAINTAIN
            self.complete_pages[page_no] = self.buffering_pages[page_no]
            del self.buffering_pages[page_no]

    def send_data(self, page_number, packet_number):
        try:
            data = DelugePDU.create_data_packet(
                self.version, page_number, packet_number,
                self.complete_pages[page_number][packet_number])
            self.send(data.to_string())
        except KeyError:
            pass

    def send_req(self, page_number, packets):
        req = DelugePDU.create_req_packet(self.version, page_number, packets)
        self.send(req.to_string())

    def log(self, data_unit, metadata):
        # tmp. figure out something cleaner.
        if data_unit.is_adv():
            msg = "%s, %s" % (data_unit.pages, data_unit.packets_per_page)
        elif data_unit.is_req():
            msg = "%s, %s" % (data_unit.page_number, data_unit.packets)
        elif data_unit.is_data():
            msg = "%s, %s" % (data_unit.page_number, data_unit.packet_number)
        self.logger.debug("(%s, %s): Received: %s, %s From: %s" % \
            (self.addr, self.state, data_unit.get_msg_type(), msg,
                metadata.sender_addr))

    def get_page(self):
        data = []
        for page_no in xrange(len(self.packets_per_page)):
            page = self.complete_pages[page_no]
            data.extend(page[i] for i in xrange(self.packets_per_page[page_no]))
        return "".join(data)
