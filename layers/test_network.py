from nose.tools import eq_
from nose.tools import ok_
import layers


class TestNetwork(object):
    def setup(self):
        self.id = 123
        self.short_data = "This is a message."
        self.long_data = "This is a message." * 200
        self.network_layer = layers.network.Network(self.id)

    def teardown(self):
        pass

    def test_get_next_message_id(self):
        eq_(1, self.network_layer.get_next_message_id())
        eq_(2, self.network_layer.get_next_message_id())
        eq_(3, self.network_layer.get_next_message_id())

    def test_round_trip_short(self):
        self.network_layer.process_outgoing(self.short_data)
        while not self.network_layer.is_outgoing_empty():
            chunk, metadata = self.network_layer.get_outgoing()
            self.network_layer.process_incoming(chunk)
        ok_(not self.network_layer.is_incoming_empty())
        data, metadata = self.network_layer.get_incoming()
        eq_(self.short_data, data)

    def test_round_trip_long(self):
        self.network_layer.process_outgoing(self.long_data)
        while not self.network_layer.is_outgoing_empty():
            chunk, metadata = self.network_layer.get_outgoing()
            self.network_layer.process_incoming(chunk)
        ok_(not self.network_layer.is_incoming_empty())
        data, metadata = self.network_layer.get_incoming()
        eq_(self.long_data, data)
