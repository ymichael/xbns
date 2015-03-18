import app.protocol.base
import coding.message
import datetime
import hashlib
import math
import pickle
import random
import struct
import threading
import time
import utils.pdu


DATA_HASH_SIZE = 7


class DelugePDU(utils.pdu.PDU):
    TYPES = ["ADV", "REQ", "DATA"]

    # version, largest_completed_page, total_pages
    ADV_HEADER = "III"
    ADV_HEADER_SIZE = struct.calcsize(ADV_HEADER) # 12 bytes

    # I: unsigned int
    # version, page_number, packet_number
    DATA_HEADER = "III"
    DATA_HEADER_SIZE = struct.calcsize(DATA_HEADER) # 12 bytes

    # version, page_number
    REQ_HEADER = "HII"
    REQ_HEADER_SIZE = struct.calcsize(REQ_HEADER)

    def _init_adv(self):
        self.version, self.largest_completed_page, self.total_pages = \
            struct.unpack(self.ADV_HEADER, self.message[:self.ADV_HEADER_SIZE])
        self.data_hash = self.message[self.ADV_HEADER_SIZE:self.ADV_HEADER_SIZE + DATA_HASH_SIZE]
        known_completed = self.message[self.ADV_HEADER_SIZE + DATA_HASH_SIZE:]
        if known_completed == "":
            self.known_completed = []
        else:
            self.known_completed = struct.unpack('B' * len(known_completed), known_completed)

    def _init_req(self):
        self.request_from, self.version, self.page_number = \
            struct.unpack(self.REQ_HEADER, self.message[:self.REQ_HEADER_SIZE])
        packets = self.message[self.REQ_HEADER_SIZE:]
        self.packets = struct.unpack('B' * len(packets), packets)

    def _init_data(self):
        self.version, self.page_number, self.packet_number = \
            struct.unpack(self.DATA_HEADER, self.message[:self.DATA_HEADER_SIZE])
        self.data = self.message[self.DATA_HEADER_SIZE:]

    def _repr_adv(self):
        return "%4s, %2s, %2s, %3s, %s, %s" % \
            (self.type, self.version, self.largest_completed_page,
                    self.total_pages, self.data_hash, self.known_completed)

    def _repr_req(self):
        return "%4s, request_from: %s, %2s %s" % \
            (self.type, self.request_from, self.page_number, self.packets)

    def _repr_data(self):
        return "%4s, %2s, %2s" % (self.type, self.page_number, self.packet_number)

    @classmethod
    def create_adv(cls, version, largest_completed_page, total_pages, data_hash,
            known_completed=None):
        header = struct.pack(cls.ADV_HEADER, version, largest_completed_page, total_pages)
        data_hash = data_hash[:DATA_HASH_SIZE] if data_hash is not None else ("_" * DATA_HASH_SIZE)
        # Piggyback known completed neighbours in ADV.
        if known_completed is not None:
            known_completed = struct.pack('B' * len(known_completed), *known_completed)
        else:
            known_completed = ""
        return cls(cls.ADV, header + data_hash + known_completed)

    @classmethod
    def create_data(cls, version, page_number, packet_number, data):
        header = struct.pack(cls.DATA_HEADER, version, page_number, packet_number)
        return cls(cls.DATA, header + data)

    @classmethod
    def create_req(cls, request_from, version, page_number, packets):
        header = struct.pack(cls.REQ_HEADER, request_from, version, page_number)
        message = struct.pack('B' * len(packets), *packets)
        return cls(cls.REQ, header + message)


class DelugeState(object):
    """Enum of the states of the Deluge Protocol."""
    MAINTAIN = 'MAIN'
    RX = 'RX'
    TX = 'TX'


class Deluge(app.protocol.base.Base):
    PAGE_SIZE = 1020
    # 100 (frame size) - 16 (datalink) - 8 (transport) - 1 (PDU) - 12 (DATA HEADER) = 63
    PACKET_SIZE = 60
    PACKETS_PER_PAGE = PAGE_SIZE / PACKET_SIZE

    # Bounds for the length of each round.
    T_MIN = 1
    T_MAX = 60 * 10 # 10 minutes

    #########################
    # REQ related parameters.
    ########################
    # Send REQ after random delay between [0, T_R]
    T_R = .5
    # Packet Transmission time.
    T_TX = .2
    # Number of T_TX to wait before sending another REQ.
    W = 10
    # Max number of REQ to send before returning to MAINTAIN state. (lamda in
    # the paper.)
    RX_MAX = 2

    # Threshold of overheard packets for message suppression.
    K = 1

    # Time taken for a single frame to leave the node #send is called.
    FRAME_DELAY = .02

    # Classes to use
    PDU_CLS = DelugePDU
    STATE_CLS = DelugeState

    def process_outgoing(self, data):
        data, version = data
        version = version or (self.version + 1)
        self.new_version(version, data)

    def new_version(self, version, data, force=False, start=True):
        # Only update if the version is later than the current version.
        if version <= self.version and not force:
            return

        self.version = version
        self.complete_pages = []
        self.buffering_pages = {}
        self._split_data_into_pages_and_packets(data)
        assert self.get_data() == data
        self.total_pages = len(self.complete_pages)
        self.set_data_hash(self.get_data())

        # Only set inconsistent if version is greater than 1. The protocol is
        # started with v1 data so every node is in the "steady state" (also
        # allows more consistent experiments to be conducted).
        if version > 1:
            self._set_inconsistent()
        if start:
            self._start_next_round(delay=0)

    def _split_data_into_pages_and_packets(self, data):
        message = coding.message.Message(data)
        pad_to_size = len(message) + self.PAGE_SIZE
        pad_to_size -= pad_to_size % self.PAGE_SIZE
        data = message.to_size(pad_to_size)
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

    def get_data(self):
        packets = []
        for page in self.complete_pages:
            for packet_number in xrange(self.PACKETS_PER_PAGE):
                packets.append(page[packet_number])
        m = coding.message.Message.from_string("".join(packets))
        return m.string

    def set_data_hash(self, data):
        self.data_hash = hashlib.md5(data).hexdigest()

    def check_if_completed(self):
        if len(self.complete_pages) == self.total_pages:
            data = self.get_data()
            self.set_data_hash(data)
            self.received(data)

    def __init__(self):
        super(Deluge, self).__init__()

        # The current version
        self.version = 1

        # An MD5 hash of the current data.
        self.data_hash = None

        # The number of pages in the current version.
        self.total_pages = 0

        # The current round.
        self.round_number = 0

        # The number of rounds in the current state.
        self.rounds_in_state = 0

        # Page/Packet information.
        self.complete_pages = []
        self.buffering_pages = {}

        # Timers and threads
        self._send_adv_timer = None
        self._send_req_timer = None
        self._next_round_timer = None

        self._stopped = False
        self._known_completed = set()

        self._reset_round_state()

    def _reset_round_state(self):
        # The state of the protocols. Starts in the MAINTAIN state.
        self.state = self.STATE_CLS.MAINTAIN

        # The length of the window. This is dynamically adjusted to be between
        # T_MIN and T_MAX to allow for fast propagation of new versions and low
        # maintainance overhead.
        self.t = self.T_MAX

        # Number of ADV overheard with similar summaries.
        self.adv_overheard = 0

        # Number of REQ/DATA overheard
        self.req_and_data_overheard = 0

        # Number of REQ/DATA overheard in the previous W*TX + r
        self.req_and_data_overheard_buffer = 0

        # DATA rate in the RX state (to determine if we should exit RX state)
        self._rx_data_rate = 0

        # A buffer of DATA (page, packet) tuples to send.
        self._pending_datas = set()

        # Whether network is inconsistent based on the packets heard during the
        # current round.
        self._inconsistent = False

        # The page to be requested. Also the page that cause the transition
        # from the MAINTAIN to the RX state.
        self._page_to_req = None

        # The latest node that sent an ADV that fulfills the `_page_to_req`.
        # Initially, when changing from MAINTAIN to RX, this is the node that
        # triggered entry into the RX state.
        self._rx_source = None

        # The number of REQ sent since entering the RX state.
        self._rx_num_sent = 0

        # [time, req_pdu, sender] of the last req packet received.
        self._last_req_packet_recieved = (None, None, None)

        # [time, data_pdu, sender] of the last data packet received.
        self._last_data_packet_received = (None, None, None)

    def start(self):
        if self._stopped:
            self._start_next_round()

    def stop(self):
        self._stopped = True
        self._cancel_all_timers()

    def _cancel_all_timers(self):
        if self._send_adv_timer is not None:
            self._send_adv_timer.cancel()
        if self._send_req_timer is not None:
            self._send_req_timer.cancel()
        if self._next_round_timer is not None:
            self._next_round_timer.cancel()

    def _start_next_round(self, delay=0):
        self._stopped = False
        self._cancel_all_timers()
        self._next_round_timer = threading.Timer(delay, self._round)
        self._next_round_timer.start()

    def _set_inconsistent(self):
        self._inconsistent = True
        self.t = self.T_MIN

    def _round(self):
        # Reset round state.
        self.adv_overheard = 0
        self.round_number += 1
        self.req_and_data_overheard_buffer = self.req_and_data_overheard
        self.req_and_data_overheard = 0
        self.rounds_in_state += 1

        self._log_round()
        if self.state == self.STATE_CLS.MAINTAIN:
            self._round_maintain()
        elif self.state == self.STATE_CLS.RX:
            self._round_rx()
        elif self.state == self.STATE_CLS.TX:
            self._round_tx()

    def _round_maintain(self):
        if not self._inconsistent:
            self.t = min(2 * self.t, self.T_MAX)
        self._inconsistent = False

        self._start_next_round(delay=self.t)
        self._send_adv_delayed()

    def _round_rx(self):
        self._maybe_exit_rx()
        self._start_next_round(delay=self.W * self.T_TX)
        self._send_req_delayed()

    def _round_tx(self):
        self._send_data()
        self._start_next_round(delay=0)

    def _send_adv_delayed(self):
        # Wait for a random amount of time (between self.t / 2 and self.t)
        rand_t = self._get_random_t_adv()
        if self._send_adv_timer is not None:
            self._send_adv_timer.cancel()
        self._send_adv_timer = threading.Timer(rand_t, self._send_adv)
        self._send_adv_timer.start()

    def _send_adv(self, force=False):
        # Only send ADV if during the current window, we overhear less than K
        # summaries with similar (v, pages).
        if self.adv_overheard >= self.K and not force:
            self._log("Suppressed ADV")
            return
        adv = self.PDU_CLS.create_adv(self.version,
            len(self.complete_pages), self.total_pages,
            self.data_hash, self._known_completed)
        self._send_pdu(adv)

    def _send_req_delayed(self):
        rand_t = self._get_random_t_req()
        if self._send_req_timer is not None:
            self._send_req_timer.cancel()
        self._send_req_timer = threading.Timer(rand_t, self._send_req)
        self._send_req_timer.start()

    def _send_req(self):
        if self.req_and_data_overheard_buffer or \
                self.req_and_data_overheard or self._page_to_req is None:
            self._log("Suppressed REQ")
            return
        self._rx_num_sent += 1
        self._send_pdu(self._create_req())

    def _create_req(self):
        if self._page_to_req not in self.buffering_pages:
            current_packets = set()
        else:
            current_packets = set(self.buffering_pages[self._page_to_req].keys())
        missing_packets = set(xrange(self.PACKETS_PER_PAGE)) - current_packets
        return self.PDU_CLS.create_req(
            self._rx_source, self.version, self._page_to_req, missing_packets)

    def _maybe_exit_rx(self):
        # If DATA rate of the previous round is poor (less than 1 useful DATA
        # packet was received, useful: missing and belonging to the page that
        # triggered entry into the RX state). Exit RX State.
        if self._rx_num_sent >= self.RX_MAX and \
                self._rx_data_rate < 1:
            self._log("DATA rate too low.")
            self._exit_rx()
            self._start_next_round(delay=0)

        # Reset counter.
        self._rx_data_rate = 0

    def _send_data(self):
        while len(self._pending_datas):
            page, packet = self._pending_datas.pop()
            data = self.PDU_CLS.create_data(
                self.version, page, packet,
                self.complete_pages[page][packet])
            sent_data = self._send_pdu(data)
            # NOTE: sleep for a short amount of time. (.2s per frame)
            # Instead of getting an acknowledgement from the networking stack
            # that the message has been sent.
            time.sleep(math.ceil(len(sent_data) / 76.0) * self.FRAME_DELAY)
        self._change_state(self.STATE_CLS.MAINTAIN)

    def _handle_incoming_message(self, message, sender_addr):
        data_unit = self.PDU_CLS.from_string(message)
        self._log_receive_pdu(data_unit, sender_addr)
        if self._stopped:
            return

        # Update state if applicable (only in MAINTAIN state since we might be
        # in the midst of RX/TX)
        # TODO: More complext but if in RX/TX, stop requesting/transmitting.
        if self.state == self.STATE_CLS.MAINTAIN and \
                data_unit.version > self.version:
            self.version = data_unit.version
            self.buffering_pages = {}
            self.complete_pages = []
            self.total_pages = 0
            self._known_completed = set()

        # Record state regarding overheard REQ and DATA packets
        if data_unit.is_req() or data_unit.is_data():
            self.req_and_data_overheard += 1
        if data_unit.is_req() and \
                data_unit.page_number < len(self.complete_pages):
            self._last_req_packet_recieved = (datetime.datetime.now(), data_unit, sender_addr)
        if data_unit.is_data() and \
                data_unit.page_number <= len(self.complete_pages):
            self._last_data_packet_received = (datetime.datetime.now(), data_unit, sender_addr)

        if data_unit.is_adv():
            self._process_adv(data_unit, sender_addr)
        elif data_unit.is_req():
            self._process_req(data_unit)
        elif data_unit.is_data():
            self._process_data(data_unit)

        # M2: If in MAINTAIN_STATE and any packet indicates inconsistency,
        # restart round.
        if self.state == self.STATE_CLS.MAINTAIN:
            if data_unit.is_req() or data_unit.is_data():
                self._set_inconsistent()
                self._start_next_round(delay=0)
                return

    def _process_adv(self, data_unit, sender_addr):
        # Only process ADV in MAINTAIN state.
        if self.state != self.STATE_CLS.MAINTAIN:
            # If in RX state, maybe update rx_source if ADV can fulfill the
            # page currently requesting.
            if self.state == self.STATE_CLS.RX and \
                    data_unit.version == self.version and \
                    data_unit.largest_completed_page >= self._page_to_req:
                self._rx_source = sender_addr
            return

        if data_unit.version == self.version and \
                data_unit.total_pages != 0:
            # Update total_pages.
            self.total_pages = data_unit.total_pages

            # Update known completed info.
            for n in data_unit.known_completed:
                self._known_completed.add(n)
            self._known_completed.add(sender_addr)

        # Check if network is consistent.
        if data_unit.version == self.version and \
                data_unit.largest_completed_page == len(self.complete_pages):
            # Network is consistent if summary overheard is similar to self.
            self.adv_overheard += 1
            return

        # Network is not consistent.
        self._set_inconsistent()

        # Check if we are ahead, if so, immediately start next round.
        if data_unit.version < self.version:
            self._start_next_round(delay=0)
            return

        # Check if there is a page we need.
        if data_unit.largest_completed_page > len(self.complete_pages):
            # M5: transit to RX unless, a REQ for a page we can fulfill was
            # overheard within the last 2 rounds OR a DATA for a page we want/
            # can fulfil was overheard in the last round.
            now = datetime.datetime.now()
            overheard_data_recently = self._last_data_packet_received[0] and \
                (now - self._last_data_packet_received[0]).total_seconds() <= self.t and \
                self._last_data_packet_received[1].version == self.version
            overheard_req_recently = self._last_req_packet_recieved[0] and \
                (now - self._last_req_packet_recieved[0]).total_seconds() <= (2 * self.t)
            if overheard_req_recently or overheard_data_recently:
                self._log("SUPPRESS TRANSITION INTO RX. %s, %s" % (overheard_req_recently, overheard_data_recently))
                # NOTE: For analysis on why suppression occurred.
                import pprint
                since_last_data = self._last_data_packet_received[0] and now - self._last_data_packet_received[0]
                since_last_req = self._last_req_packet_recieved[0] and now - self._last_req_packet_recieved[0]
                why_suppress = [
                    'now', now, 't', self.t,
                    'last_data', self._last_data_packet_received, since_last_data,
                    'last_req', self._last_req_packet_recieved, since_last_req,
                ]
                pprint.pprint(why_suppress)
            else:
                self._enter_rx(sender_addr)

        # Start next round immediately.
        self._start_next_round(delay=0)

    def _process_req(self, data_unit):
        # React to REQ, transit to TX state if we have the requested page.
        if not (data_unit.page_number < len(self.complete_pages)):
            return
        # Only process is REQ was meant for us.
        if data_unit.request_from != self.addr:
            return
        # We are able to fulfill request.
        if self.state == self.STATE_CLS.MAINTAIN:
            self._change_state(self.STATE_CLS.TX)
            for packet in data_unit.packets:
                self._pending_datas.add((data_unit.page_number, packet))
            self._start_next_round(delay=0)
        elif self.state == self.STATE_CLS.TX:
            for packet in data_unit.packets:
                self._pending_datas.add((data_unit.page_number, packet))

    def _process_data(self, data_unit):
        # Remove from pending DATA if applicable.
        data_id = (data_unit.page_number, data_unit.packet_number)
        if data_id in self._pending_datas:
            self._log("Suppressed DATA")
            self._pending_datas.remove(data_id)

        # Store data if applicable.
        if data_unit.page_number >= len(self.complete_pages):
            if data_unit.page_number not in self.buffering_pages:
                self.buffering_pages[data_unit.page_number] = {}
            if data_unit.packet_number not in self.buffering_pages[data_unit.page_number]:
                self.buffering_pages[data_unit.page_number][data_unit.packet_number] = data_unit.data

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
            self.check_if_completed()
            if self.state == self.STATE_CLS.RX and next_page == self._page_to_req:
                self._exit_rx()
            del self.buffering_pages[next_page]
            next_page += 1

    def _enter_rx(self, rx_source):
        # Set the next page to be requested.
        self._page_to_req = len(self.complete_pages)
        self._rx_source = rx_source
        self._rx_num_sent = 0
        self._change_state(self.STATE_CLS.RX)

    def _exit_rx(self):
        self._page_to_req = None
        self._rx_source = None
        self._rx_num_sent = 0
        self._change_state(self.STATE_CLS.MAINTAIN)

    def _send_pdu(self, data_unit):
        self._log_send_pdu(data_unit)
        string = data_unit.to_string()
        self._send(string)
        # Return the string being sent.
        return string

    def _change_state(self, new_state):
        self._log_change_state(new_state)
        self.state = new_state
        self.rounds_in_state = 0

    def _log(self, message):
        prefix = "(%2s, %5s, [v%s, %02d/%02d], %4s)" % \
            (self.addr, self.state, self.version, len(self.complete_pages),
                (self.total_pages or 0), self.t)
        self.logger.info("%s - %s" % (prefix, message))

    def _log_send_pdu(self, data_unit):
        self._log("Sending message (%s): %s" % (len(data_unit.to_string()), repr(data_unit)))

    def _log_receive_pdu(self, data_unit, sender_addr):
        self._log("Received message from %3s: %s" % (sender_addr, repr(data_unit)))

    def _log_round(self):
        self._log('Starting round %3s' % self.round_number)

    def _log_change_state(self, new_state):
        self._log("Changing state from %5s to %5s" % (self.state, new_state))

    def _get_random_t_adv(self):
        return random.uniform(self.t / 2.0, self.t)

    def _get_random_t_req(self):
        return random.uniform(0, self.T_R)
