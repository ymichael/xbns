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


class Deluge(net.layers.application.Application):
    PORT = 11
    PAGE_SIZE = 1000
    PACKET_SIZE = 100

    def __init__(self):
        super(Deluge, self).__init__()
        self.current_version = 0
        self.current_pages = {}
        self.packets_per_page = []
        self.buffering_pages = {}

        self.should_adv = 1
        self.requested = set()

    def get_port(self):
        return self.PORT

    def new_version(self, version, data=None):
        if version <= self.current_version:
            return

        self.current_version = version
        self.current_pages = {}
        self.packets_per_page =[]
        self.buffering_pages = {}

        if data is not None:
            self.split_and_set_pages(data)
            self.send_adv()

    def split_and_set_pages(self, data):
        i = 0
        page_number = 0
        while i < len(data):
            page = data[i:i + self.PAGE_SIZE]
            packets = {}
            packet_number = 0
            j = 0
            while j < len(page):
                packets[packet_number] = page[j:j + self.PACKET_SIZE]
                packet_number += 1
                j += self.PACKET_SIZE
            self.current_pages[page_number] = packets
            self.packets_per_page.append(len(packets))
            page_number += 1
            i += self.PAGE_SIZE

    def send_adv(self):
        adv = DelugePDU.create_adv_packet(
            self.current_version, self.current_pages.keys(),
            self.packets_per_page)
        self.send(adv.to_string())

    def send_req(self, page_number, packets):
        req = DelugePDU.create_req_packet(
            self.current_version, page_number, packets)
        self.send(req.to_string())

    def send_data(self, page_number, packet_number):
        data = DelugePDU.create_data_packet(
            self.current_version, page_number, packet_number,
            self.current_pages[page_number][page_number])
        self.send(data.to_string())

    def start(self, *args, **kwargs):
        super(Deluge, self).start(*args, **kwargs)
        # Start thread to send ADV.
        t1 = threading.Thread(target=self.maybe_send_adv)
        t1.setDaemon(True)
        t1.start()

    def maybe_send_adv(self):
        # Only send adv if have
        while True:
            if len(self.current_pages) != 0:
                if self.should_adv == 1:
                    self.send_adv()
                else:
                    self.should_adv += 1
            time.sleep(random.random())

    def delayed_send_requested(self):
        time.sleep(1)
        for page, packet in self.requested:
            self.send_data(page, packet)
        self.requested = set()

    def send_requested(self):
        t1 = threading.Thread(target=self.delayed_send_requested)
        t1.setDaemon(True)
        t1.start()

    def log(self, data_unit, metadata):
        # tmp. figure out something cleaner.
        if data_unit.is_adv():
            msg = "%s, %s" % (data_unit.pages, data_unit.packets_per_page)
        elif data_unit.is_req():
            msg = "%s, %s" % (data_unit.page_number, data_unit.packets)
        elif data_unit.is_data():
            msg = "%s, %s" % (data_unit.page_number, data_unit.packet_number)
        self.logger.debug("(%s, %s): Received: %s, %s From: %s" % \
            (self.addr, self.get_port(), data_unit.get_msg_type(), msg,
                metadata.sender_addr))

    def process_incoming(self, data, metadata=None):
        data_unit = DelugePDU.from_string(data)
        self.log(data_unit, metadata)
        if data_unit.is_adv():
            self.process_adv(data_unit)
        elif data_unit.is_req():
            self.process_req(data_unit)
        elif data_unit.is_data():
            self.process_data(data_unit)

    def suppress_adv(self):
        self.should_adv -= 1

    def process_adv(self, data_unit):
        # Maybe update version number.
        self.new_version(data_unit.version)
        self.packets_per_page = data_unit.packets_per_page

        # Ignore if we already have all pages.
        adv_pages = set(data_unit.pages)
        own_pages = self.current_pages.keys()
        if len(adv_pages) >= len(own_pages):
            self.suppress_adv()

        missing_pages = adv_pages.difference(own_pages)
        if len(missing_pages) == 0:
            return

        # Send REQ for the lowest number page/packet we are missing.
        # If currently buffering pages, request for missing packets in these pages.
        if len(self.buffering_pages) != 0:
            incomplete_page = min(self.buffering_pages.keys())
            all_packets_in_page = set(xrange(self.packets_per_page[incomplete_page]))
            received_packets = self.buffering_pages[incomplete_page].keys()
            missing_packets = all_packets_in_page.difference(received_packets)
            self.send_req(incomplete_page, missing_packets)
        else:
            missing_page = min(missing_pages)
            self.send_req(
                missing_page, list(range(self.packets_per_page[missing_page])))

    def process_req(self, data_unit):
        # Ignore REQ is we don't have the page.
        requested_page = data_unit.page_number
        if requested_page not in self.current_pages:
            return
        # Send out missing packets
        for packet_number in data_unit.packets:
            self.requested.add((requested_page, packet_number))

        self.send_requested()

    def process_data(self, data_unit):
        # Ignore DATA if wrong version.
        if self.current_version != data_unit.version:
            return

        # Ignore DATA is we already have the page
        page = data_unit.page_number
        if page in self.current_pages:
            return

        if page not in self.buffering_pages:
            self.buffering_pages[page] = {}

        # Ignore if we already have the packet.
        packet = data_unit.packet_number
        if packet in self.buffering_pages[page]:
            return

        self.buffering_pages[page][packet] = data_unit.message
        # If fullpage, move buffered page into current pages.
        if len(self.buffering_pages[page]) == self.packets_per_page[page]:
            self.current_pages[page] = self.buffering_pages[page]
            del self.buffering_pages[page]

        if len(self.current_pages) == len(self.packets_per_page):
            self.logger.debug("(%s, %s): Done." % (self.addr, self.get_port()))
