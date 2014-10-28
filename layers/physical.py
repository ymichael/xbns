import base
import threading


BROADCAST_ADDRESS = "\xFF\xFF"


class Physical(base.BaseLayer):
    """Physical layer, interfaces with the XBee."""
    def __init__(self, xbee):
        super(Physical, self).__init__();
        self.xbee = xbee
        self.panid = None
        self.myid = None
        self.channel = None

    def process_outgoing(self, data, metadata=None):
        self.broadcast(data)

    def broadcast(self, data):
        # TODO: Some logging here.
        # Maximum data size is 100.
        assert len(data) <= 100
        self.xbee.tx(dest_addr=BROADCAST_ADDRESS, data=data)

    def listen_to_xbee(self):
        while True:
            frame = self.xbee.wait_read_frame()
            self.put_incoming(frame.get('rf_data'))

    def start(self, incoming_layer=None, outgoing_layer=None):
        super(Physical, self).start(outgoing_layer=outgoing_layer)
        t = threading.Thread(target=self.listen_to_xbee)
        t.setDaemon(True)
        t.start()

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

    def at_command(self, cmd, param):
        # TODO: frame_id, if specified will yield a response (with information
        # on the outcome of the command).
        self.xbee.at(command=cmd, parameter=param)
