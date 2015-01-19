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
            self._init_adv()
        elif self.is_req():
            self._init_req()
        elif self.is_data():
            self._init_data()

    def _init_adv(self):
        self.version, self.largest_completed_page = pickle.loads(self.message)

    def _init_req(self):
        self.version, self.page_number, self.packets = pickle.loads(self.message)

    def _init_data(self):
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
    MAINTAIN = 'MAIN'
    RX = 'RX'
    TX = 'TX'


class Deluge(net.layers.application.Application):
    PORT = 11
    PAGE_SIZE = 1000
    PACKET_SIZE = 100
    PACKETS_PER_PAGE = 10

    # Bounds for the length of each round.
    T_MIN = 1
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

        self._set_inconsistent()
        self._start_next_round(delay=0)

    def _split_data_into_pages_and_packets(self, data):
        # TODO: Handle padding of variable length data.
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

        # The current round.
        self.round_number = 0

        # The number of rounds in the current state.
        self.rounds_in_state = 0

        # Page/Packet information.
        self.complete_pages = []
        self.buffering_pages = {}

        # The state of the protocols. Starts in the MAINTAIN state.
        self.state = DelugeState.MAINTAIN

        # The length of the window. This is dynamically adjusted to be between
        # T_MIN and T_MAX to allow for fast propagation of new versions and low
        # maintainance overhead.
        self.t = self.T_MAX

        # Number of ADV overheard with similar summaries.
        self.adv_overheard = 0

        # Number of REQ/DATA overheard
        self.req_and_data_overheard = 0

        # DATA rate in the DelugeState.RX state (to determine if we should exit
        # RX state)
        self._rx_data_rate = 0

        # A buffer of DATA (page, packet) tuples to send.
        self._pending_datas = set()

        # Whether network is inconsistent based on the packets heard during the
        # current round.
        self._inconsistent = False

        # The page to be requested. Also the page that cause the transition
        # from the MAINTAIN to the RX state.
        self._page_to_req = None

        # Timers and threads
        self._send_adv_timer = None
        self._send_req_timer = None
        self._send_data_timer = None
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

    def _set_inconsistent(self):
        self._inconsistent = True
        self.t = self.T_MIN

    def _round(self):
        # Reset round state.
        self.req_and_data_overheard = 0
        self.adv_overheard = 0
        self.round_number += 1
        self.rounds_in_state += 1

        self._log_round()
        if self.state == DelugeState.MAINTAIN:
            self._round_maintain()
        elif self.state == DelugeState.RX:
            self._round_rx()
        elif self.state == DelugeState.TX:
            self._round_tx()

    def _round_maintain(self):
        if not self._inconsistent:
            self.t = min(2 * self.t, self.T_MAX)
        self._inconsistent = False

        self._start_next_round(delay=self.t)
        self._send_adv_delayed()

    def _round_rx(self):
        self._maybe_exit_rx()
        self._start_next_round(delay=self.t)
        self._send_req_delayed()

    def _round_tx(self):
        self._start_next_round(delay=self.t)
        self._send_data_delayed()

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
            self.log("Suppressed ADV")
            return
        adv = DelugePDU.create_adv_packet(self.version, len(self.complete_pages))
        self._send_pdu(adv)

    def _send_req_delayed(self):
        rand_t = self._get_random_t_req()
        if self._send_req_timer is not None:
            self._send_req_timer.cancel()
        self._send_req_timer = threading.Timer(rand_t, self._send_req)
        self._send_req_timer.start()

    def _send_req(self):
        if self.req_and_data_overheard or self._page_to_req is None:
            self.log("Suppressed REQ")
            return
        current_packets = set(self.buffering_pages[self._page_to_req].keys())
        missing_packets = set(xrange(self.PACKETS_PER_PAGE)) - current_packets
        req = DelugePDU.create_req_packet(self.version, self._page_to_req, missing_packets)
        self._send_pdu(req)

    def _maybe_exit_rx(self):
        # Don't exit in the first round.
        # If DATA rate of the previous round is poor (less than 1 useful DATA
        # packet was received, useful: missing and belonging to the page that
        # triggered entry into the RX state). Exit RX State.
        if self.rounds_in_state != 1 and \
                self._rx_data_rate < 1:
            self.log("DATA rate too low.")
            self._change_state(DelugeState.MAINTAIN)

        # Reset counter.
        self._rx_data_rate = 0

    def _send_data_delayed(self):
        rand_t = self._get_random_t_tx()
        if self._send_data_timer is not None:
            self._send_data_timer.cancel()
        self._send_data_timer = threading.Timer(rand_t, self._send_data)
        self._send_data_timer.start()

    def _send_data(self):
        while len(self._pending_datas):
            page, packet = self._pending_datas.pop()
            data = DelugePDU.create_data_packet(
                self.version, page, packet,
                self.complete_pages[page][packet])
            self._send_pdu(data)
        self._change_state(DelugeState.MAINTAIN)

    def process_incoming(self, data, metadata=None):
        data_unit = DelugePDU.from_string(data)
        self._log_receive_pdu(data_unit, metadata)

        if data_unit.is_adv():
            self._process_adv(data_unit)
        elif data_unit.is_req():
            self._process_req(data_unit)
        elif data_unit.is_data():
            self._process_data(data_unit)

    def _process_adv(self, data_unit):
        # Check if network is consistent.
        if data_unit.version > self.version:
            self.version = data_unit.version
            self.buffering_pages = {}
            self.complete_pages = []
        
        if data_unit.largest_completed_page == len(self.complete_pages):
            # Network is consistent if summary overheard is similar to self.
            self.adv_overheard += 1
            return

        # Network is inconsistent.
        self._set_inconsistent()

        if data_unit.largest_completed_page > len(self.complete_pages):
            # Self not up-to-date.
            if self.state == DelugeState.MAINTAIN:
                # Set the next page to be requested.
                self._page_to_req = len(self.complete_pages)
                if self._page_to_req not in self.buffering_pages:
                    self.buffering_pages[self._page_to_req] = {}
                self._change_state(DelugeState.RX)
                self._start_next_round(delay=0)

    def _process_req(self, data_unit):
        self.req_and_data_overheard += 1
        # REQ indicates that network is not up-to-date.
        self._set_inconsistent()

        # React to REQ, transit to TX state if we have the requested page.
        if data_unit.page_number < len(self.complete_pages):
            # We are able to fulfill request.
            if self.state == DelugeState.MAINTAIN:
                self._change_state(DelugeState.TX)
                for packet in data_unit.packets:
                    self._pending_datas.add((data_unit.page_number, packet))
                self._start_next_round(delay=0)

    def _process_data(self, data_unit):
        self.req_and_data_overheard += 1
        # DATA indicates that network is not up-to-date.
        self._set_inconsistent()

        # Remove from pending DATA if applicable.
        data_id = (data_unit.page_number, data_unit.packet_number)
        if data_id in self._pending_datas:
            self.log("Suppressed DATA")
            self._pending_datas.remove(data_id)

        # Store data if applicable.
        if data_unit.page_number >= len(self.complete_pages):
            if data_unit.page_number not in self.buffering_pages:
                self.buffering_pages[data_unit.page_number] = {}
            if data_unit.packet_number not in self.buffering_pages[data_unit.page_number]:
                self.buffering_pages[data_unit.page_number][data_unit.packet_number] = data_unit.message

                # Received a DATA packet for the page that triggered entry to
                # the RX state.
                if data_unit.page_number == self._page_to_req:
                    self._rx_data_rate += 1

        # If we complete the next page, move it (and all applicable pages) to
        # the completed pages.
        next_page = len(self.complete_pages)
        while next_page in self.buffering_pages and \
                len(self.buffering_pages[next_page]) == self.PACKETS_PER_PAGE:
            self.complete_pages.append(self.buffering_pages[next_page])
            if self.state == DelugeState.RX and next_page == self._page_to_req:
                self._page_to_req = None
                self._change_state(DelugeState.MAINTAIN)
            del self.buffering_pages[next_page]
            next_page += 1

    def _send_pdu(self, data_unit):
        self._log_send_pdu(data_unit)
        self.send(data_unit.to_string())

    def _change_state(self, new_state):
        self._log_change_state(new_state)
        self.state = new_state
        self.rounds_in_state = 0

    def log(self, message):
        prefix = "(%2s, %5s, %3s, %4s)" % \
            (self.addr, self.state, len(self.complete_pages), self.t)
        print "%s - %s" % (prefix, message)

    def _log_send_pdu(self, data_unit):
        msg = ""
        if data_unit.is_adv():
            msg += "%4s, %2s, %2s" % \
                (data_unit.type, data_unit.version, data_unit.largest_completed_page)
        elif data_unit.is_req():
            msg += "%4s, %2s %s" % \
                (data_unit.type, data_unit.page_number, data_unit.packets)
        elif data_unit.is_data():
            msg += "%4s, %2s, %2s" % \
                (data_unit.type, data_unit.page_number, data_unit.packet_number)
        self.log("Sending message: %s" % msg)

    def _log_receive_pdu(self, data_unit, metadata):
        msg = ""
        if data_unit.is_adv():
            msg += "%4s, %2s, %2s" % \
                (data_unit.type, data_unit.version, data_unit.largest_completed_page)
        elif data_unit.is_req():
            msg += "%4s, %2s" % \
                (data_unit.type, data_unit.page_number)
        elif data_unit.is_data():
            msg += "%4s, %2s, %2s" % \
                (data_unit.type, data_unit.page_number, data_unit.packet_number)
        self.log("Received message from %3s: %s" % (metadata.sender_addr, msg))

    def _log_round(self):
        self.log('Starting round %3s' % self.round_number)

    def _log_change_state(self, new_state):
        self.log("Changing state from %5s to %5s" % (self.state, new_state))

    def _get_random_t_adv(self):
        return random.uniform(self.t / 2.0, self.t)

    def _get_random_t_req(self):
        return random.uniform(0, self.t / 2.0)

    def _get_random_t_tx(self):
        return random.uniform(0, self.t)