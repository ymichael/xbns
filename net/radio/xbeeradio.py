import base
import serial
import struct
import xbee


class XBeeRadio(base.BaseRadio):
    BROADCAST_ADDRESS = "\xFF\xFF"

    def __init__(self, xbee_module):
        super(XBeeRadio, self).__init__()
        self.xbee_module = xbee_module

    def broadcast(self, data):
        assert len(data) <= 100
        # TODO: Figure out a good sleep interval here.
        # Packet loss is fairly high if not.
        self.xbee_module.tx(dest_addr=self.BROADCAST_ADDRESS, data=data)

    def receive(self):
        frame = self.xbee_module.wait_read_frame()
        if frame.get('id') == "rx":
            data = frame.get('rf_data')
            sender_addr = struct.unpack("H", frame.get('source_addr'))[0]
            return (self.TYPE_RX, data, sender_addr)
        return (self.TYPE_OTHERS, frame)

    def tohex(self, integer):
        """Returns a hex representation of an integer.

        eg 17 -> \x11
        """
        hex_repr = hex(integer)[2:]
        if len(hex_repr) % 2 != 0:
            hex_repr = "0" + hex_repr
        return hex_repr.decode("hex")

    def fromhex(self, hexstring):
        """Returns an int representation of the hex string.

        eg \x11 -> 17
        """
        return int(hexstring.encode("hex"), 16)

    def set_myid(self, value):
        self.myid = value
        self.at_command("MY", self.tohex(value))

    def set_channel(self, value):
        self.channel = value
        self.at_command("CH", self.tohex(value))

    def set_panid(self, value):
        self.panid = value
        self.at_command("ID", self.tohex(value))

    def set_power_level(self, value):
        assert 0 <= value <= 4
        self.at_command("PL", self.tohex(value))

    def at_command(self, cmd, param):
        self.xbee_module.at(command=cmd, parameter=param)
        # Read the current setting.
        self.xbee_module.at(command=cmd, frame_id='1')

    @classmethod
    def create(cls, port, baudrate, panid, channel, myid, power_level=4):
        if not (0 <= myid <= 2**16):
            raise ValueError("Expected 16-bit Module Id, got: %s" % myid)
        if not (0 <= panid < 2**64):
            raise ValueError("Expected 64-bit PAN id, got: %s" % panid)
        if not (11 <= channel <= 26):
            raise ValueError("Expected Channel id = [11, 26], got: %s" % channel)
        # Create xbee module
        serial_object = serial.Serial(port, baudrate)
        xbee_module = xbee.XBee(serial_object, escaped=True)
        # Create radio
        radio = XBeeRadio(xbee_module)
        radio.set_panid(panid)
        radio.set_channel(channel)
        radio.set_myid(myid)
        radio.set_power_level(power_level)
        return radio