from nose.tools import eq_
from nose.tools import ok_
import layers


class TestDataLink(object):
    def setup(self):
        self.id = 123
        self.short_data = "This is a message."
        self.long_data = "This is a message." * 200
        self.data_link_layer = layers.datalink.DataLink(self.id)

    def teardown(self):
        pass

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
