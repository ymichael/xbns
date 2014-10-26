from nose.tools import eq_
from nose.tools import ok_
from mockito import *
import layers


class TestPhysical(object):
    def setup(self):
        self.id = 1
        self.panid = 2
        self.channel = 11
        self.xbee =  mock()
        self.physical_layer = layers.physical.Physical(self.xbee)

    def test_set_myid(self):
        self.physical_layer.set_myid(self.id)
        eq_(self.id, self.physical_layer.myid)
        verify(self.xbee).at(command="MY", parameter="\x01")

    def test_set_channel(self):
        self.physical_layer.set_channel(self.channel)
        eq_(self.channel, self.physical_layer.channel)
        verify(self.xbee).at(command="CH", parameter="\x0b")

    def test_set_panid(self):
        self.physical_layer.set_panid(self.panid)
        eq_(self.panid, self.physical_layer.panid)
        verify(self.xbee).at(command="ID", parameter="\x02")
