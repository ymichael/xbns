import coding.message
import coding.ff
import deluge
import itertools
import random
import struct
import time


# TODO: Fix this circular dependency.
deluge.Deluge.PAGE_SIZE = 900
# 100 (frame size) - 16 (datalink) - 8 (transport) - 1 (PDU) - 8 (DATA HEADER) = 67
# - 20 (matrix coeffs) = 47
deluge.Deluge.PACKET_SIZE = 45
deluge.Deluge.PACKETS_PER_PAGE = deluge.Deluge.PAGE_SIZE / deluge.Deluge.PACKET_SIZE
ROWS_REQUIRED = deluge.Deluge.PACKETS_PER_PAGE


class RatelessDelugePDU(deluge.DelugePDU):
    # I: unsigned int
    # version, page_number, coeffs, data
    DATA_FORMAT = "II" + ("B" * ROWS_REQUIRED) + \
        ("B" * deluge.Deluge.PACKET_SIZE)

    # request_from, version, page, num_packets
    REQ_HEADER = "HIII"

    def _init_req(self):
        self.request_from, self.version, self.page_number, self.number_of_packets = \
            struct.unpack(self.REQ_HEADER, self.message)

    def _init_data(self):
        x = struct.unpack(self.DATA_FORMAT, self.message)
        self.version = x[0]
        self.page_number = x[1]
        self.coeffs = x[2:2 + ROWS_REQUIRED]
        self.data = x[2 + ROWS_REQUIRED:]

    def _repr_req(self):
        return "%4s, request_from: %s, %2s %s" % \
            (self.type, self.request_from, self.page_number, self.number_of_packets)

    def _repr_data(self):
        return "%4s, %2s" % (self.type, self.page_number)

    @classmethod
    def create_data_packet(cls, version, page_number, coeffs, data):
        args = [version, page_number]
        args.extend(coeffs)
        args.extend(data)
        message = struct.pack(cls.DATA_FORMAT, *args)
        return cls(cls.DATA, message)

    @classmethod
    def create_req_packet(cls, request_from, version, page_number, number_of_packets):
        message = struct.pack(cls.REQ_HEADER, request_from, version,
                              page_number, number_of_packets)
        return cls(cls.REQ, message)


class RatelessDeluge(deluge.Deluge):
    ADDRESS = ("", 11003)



    PDU_CLS = RatelessDelugePDU

    def _reset_round_state(self):
        super(RatelessDeluge, self)._reset_round_state()

        # Mapping of page => number of DATA packets required.
        self._pending_datas = {}

    def _split_data_into_pages_and_packets(self, data):
        message = coding.message.Message(data)
        pad_to_size = len(message) + self.PAGE_SIZE
        pad_to_size -= pad_to_size % self.PAGE_SIZE
        data = message.to_size(pad_to_size)

        current_index = 0
        page_number = 0
        while current_index < len(data):
            page_end = current_index + self.PAGE_SIZE
            matrix = coding.ff.Matrix()
            while current_index < page_end and current_index < len(data):
                packet_end = current_index + self.PACKET_SIZE
                packet = data[current_index:packet_end]
                matrix.add_row(coding.message.Message.to_int_array(packet))
                current_index += self.PACKET_SIZE
            self.complete_pages.append(matrix)
            page_number += 1

    def get_data(self):
        packets = []
        for page in self.complete_pages:
            int_array = list(itertools.chain(*page.rows))
            packets.extend(int_array)
        message = coding.message.Message.from_string(
            coding.message.Message.int_array_to_string(packets))
        return message.string

    def _create_req(self):
        if self._page_to_req not in self.buffering_pages:
            packets_required = ROWS_REQUIRED
        else:
            packets_required = self.buffering_pages[self._page_to_req].get_rows_required()
        return self.PDU_CLS.create_req_packet(
            self._rx_source, self.version, self._page_to_req, packets_required)

    def _get_random_coeffs(self):
        m = coding.ff.Matrix()
        m.add_row([random.randint(0, 255) for i in xrange(ROWS_REQUIRED)])
        return m

    def _send_data(self):
        for page, number_of_packets in self._pending_datas.items():
            for i in xrange(number_of_packets):
                coeffs = self._get_random_coeffs()
                coded_data = coeffs.dot(self.complete_pages[page])
                data = self.PDU_CLS.create_data_packet(
                    self.version, page, list(coeffs.iter_row(0)), list(coded_data.iter_row(0)))
                self._send_pdu(data)
                # Sleep for a short amount of time.
                time.sleep(.02)
        self._pending_datas = {}
        self._change_state(self.STATE_CLS.MAINTAIN)

    def _process_req(self, data_unit):
        # React to REQ, transit to TX state only if we have the requested page.
        if not (data_unit.page_number < len(self.complete_pages)):
            return
        # Only process is REQ was meant for us.
        if data_unit.request_from != self.addr:
            return
        # We are able to fulfill request.
        if self.state == self.STATE_CLS.MAINTAIN:
            self._change_state(self.STATE_CLS.TX)
            self._pending_datas[data_unit.page_number] = \
                max(data_unit.number_of_packets,
                    self._pending_datas.get(data_unit.page_number, 0))
            self._start_next_round(delay=0)

    def _process_data(self, data_unit):
        # Remove from pending DATA if applicable.
        if data_unit.page_number in self._pending_datas:
            self.log("Suppressed DATA")
            self._pending_datas[data_unit.page_number] -= 1

        # Store data if applicable.
        if data_unit.page_number >= len(self.complete_pages):
            if data_unit.page_number not in self.buffering_pages:
                self.buffering_pages[data_unit.page_number] = coding.ff.Gaussian()
            self.buffering_pages[data_unit.page_number].add_row(data_unit.coeffs, data_unit.data)
            # Received a DATA packet for the page that triggered entry to
            # the RX state.
            if data_unit.page_number == self._page_to_req:
                self._rx_data_rate += 1

        # If we complete the next page, move it (and all applicable pages) to
        # the completed pages.
        next_page = len(self.complete_pages)
        while next_page in self.buffering_pages and self.buffering_pages[next_page].is_solved():
            matrix = self.buffering_pages[next_page].solve()
            self.complete_pages.append(matrix)
            self.check_if_completed()
            if self.state == self.STATE_CLS.RX and next_page == self._page_to_req:
                self._rx_source = None
                self._page_to_req = None
                self._change_state(self.STATE_CLS.MAINTAIN)
            del self.buffering_pages[next_page]
            next_page += 1
