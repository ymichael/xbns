from nose.tools import eq_
from nose.tools import ok_
import base
import datalink


class TestDataLink(object):
    def setup(self):
        self.addr = 123
        self.dest_addr = 124
        self.message_id = 10
        self.short_data = "This is a message."
        self.long_data = "This is a message." * 200
        self.data_link_layer = datalink.DataLink()
        self.data_link_layer.set_addr(self.addr)

    def teardown(self):
        pass

    def test_pdu_constructor(self):
        data_unit = datalink.DataLinkPDU(self.addr, self.dest_addr,
            self.message_id, 2, 100, 1, self.short_data)
        eq_(self.addr, data_unit.source_addr)
        eq_(self.dest_addr, data_unit.dest_addr)
        eq_(self.message_id, data_unit.message_id)
        eq_(100, data_unit.total_size)
        eq_(1, data_unit.piece_no)
        eq_(2, data_unit.ttl)
        eq_(self.short_data, data_unit.chunk)

    def test_pdu_round_trip(self):
        data_unit = datalink.DataLinkPDU(self.addr, self.dest_addr,
            self.message_id, 2, 100, 1, self.short_data)
        data_unit = datalink.DataLinkPDU.from_string(data_unit.to_string())
        eq_(self.addr, data_unit.source_addr)
        eq_(self.dest_addr, data_unit.dest_addr)
        eq_(self.message_id, data_unit.message_id)
        eq_(100, data_unit.total_size)
        eq_(1, data_unit.piece_no)
        eq_(2, data_unit.ttl)
        eq_(self.short_data, data_unit.chunk)

    def test_get_next_message_id(self):
        eq_(1, self.data_link_layer.get_next_message_id())
        eq_(2, self.data_link_layer.get_next_message_id())
        eq_(3, self.data_link_layer.get_next_message_id())

    def test_round_trip_short(self):
        self.data_link_layer.process_outgoing(self.short_data)
        while not self.data_link_layer.is_outgoing_empty():
            chunk, metadata = self.data_link_layer.get_outgoing()
            self.data_link_layer.process_incoming(chunk)

        ok_(not self.data_link_layer.is_incoming_empty())
        data, metadata = self.data_link_layer.get_incoming()
        eq_(self.short_data, data)

    def test_round_trip_long(self):
        self.data_link_layer.process_outgoing(self.long_data)
        while not self.data_link_layer.is_outgoing_empty():
            chunk, metadata = self.data_link_layer.get_outgoing()
            self.data_link_layer.process_incoming(chunk)

        ok_(not self.data_link_layer.is_incoming_empty())
        data, metadata = self.data_link_layer.get_incoming()
        eq_(self.long_data, data)

    def test_should_not_receive_if_not_recipient(self):
        data_unit = datalink.DataLinkPDU(
            self.addr, base.MetaData.BROADCAST_ADDR,
            self.message_id, 1, 100, 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit.to_string())
        ok_(self.data_link_layer.is_incoming_empty())

    def test_should_not_forward_broadcast(self):
        data_unit = datalink.DataLinkPDU(
            self.addr, base.MetaData.BROADCAST_ADDR,
            self.message_id, 1, 100, 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit.to_string())
        ok_(self.data_link_layer.is_outgoing_empty())

    def test_should_not_forward_if_recipient(self):
        data_unit = datalink.DataLinkPDU(
            self.addr, self.addr, self.message_id, 1, 100, 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit.to_string())
        ok_(self.data_link_layer.is_outgoing_empty())

    def test_should_not_forward_if_ttl_zero(self):
        data_unit = datalink.DataLinkPDU(
            self.addr, self.addr, self.message_id, 0, 100, 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit.to_string())
        ok_(self.data_link_layer.is_outgoing_empty())

    def test_should_forward(self):
        data_unit = datalink.DataLinkPDU(
            self.addr, self.addr + 1,
            self.message_id, 1, len(self.short_data), 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit.to_string())
        ok_(not self.data_link_layer.is_outgoing_empty())
        chunk, metadata = self.data_link_layer.get_outgoing()
        chunk = datalink.DataLinkPDU.from_string(chunk)
        eq_(data_unit.source_addr, chunk.source_addr)
        eq_(data_unit.dest_addr, chunk.dest_addr)
        eq_(data_unit.message_id, chunk.message_id)
        eq_(data_unit.total_size, chunk.total_size)
        eq_(data_unit.piece_no, chunk.piece_no)
        eq_(data_unit.chunk, chunk.chunk)

    def test_should_not_forward_if_seen(self):
        data_unit = datalink.DataLinkPDU(
            self.addr, self.addr + 1,
            self.message_id, 1, len(self.short_data), 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit.to_string())
        ok_(not self.data_link_layer.is_outgoing_empty())
        # Clear both queues.
        chunk, metadata = self.data_link_layer.get_outgoing()
        data_unit.ttl -= 1
        eq_(data_unit.to_string(), chunk)
        # Receive same data unit.
        self.data_link_layer.process_incoming(data_unit.to_string())
        ok_(self.data_link_layer.is_outgoing_empty())

    def test_should_flush_buffer(self):
        self.data_link_layer.buffer_window = 1
        data_unit1 = datalink.DataLinkPDU(
            self.dest_addr, self.addr,
            self.message_id, 1, len(self.short_data), 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit1.to_string())
        # One message buffered from self.dest_addr
        eq_(1, len(self.data_link_layer.buffer[self.dest_addr]))
        
        data_unit2 = datalink.DataLinkPDU(
            self.dest_addr, self.addr,
            self.message_id + 1, 1, len(self.short_data), 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit2.to_string())
        # two messages buffered from self.dest_addr
        eq_(2, len(self.data_link_layer.buffer[self.dest_addr]))

        data_unit3 = datalink.DataLinkPDU(
            self.dest_addr, self.addr,
            self.message_id + 2, 1, len(self.short_data), 1, self.short_data)
        self.data_link_layer.process_incoming(data_unit3.to_string())
        # two messages (the latest 2) buffered from self.dest_addr
        eq_(2, len(self.data_link_layer.buffer[self.dest_addr]))
        ok_(self.message_id + 1 in self.data_link_layer.buffer[self.dest_addr])
        ok_(self.message_id + 2 in self.data_link_layer.buffer[self.dest_addr])

