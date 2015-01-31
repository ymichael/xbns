import net.layers.application
import struct


class FloodingPDU(object):
    # version number: I
    HEADER_FORMAT = "I"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, number, message):
        self.number = number
        self.message = message

    def to_string(self):
        header = struct.pack(self.HEADER_FORMAT, self.number)
        return header + self.message

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        return FloodingPDU(x[0], data[cls.HEADER_SIZE:])


class Flooding(net.layers.application.Application):
    ADDRESS = ("", 11001)

    def __init__(self, addr):
        super(Flooding, self).__init__(addr)
        self.current_number = 0

    def _handle_incoming(self, data):
        data_unit = FloodingPDU.from_string(data)
        self.flood_update(data_unit.number, data_unit.message)

    def flood_update(self, number, update):
        if self.current_number >= number:
            return
        self.current_number = number
        self.logger.debug("(%s): Received: %s" % (self.addr, number))
        self.send(FloodingPDU(number, update).to_string())
        self.logger.debug("(%s): Sent: %s" % (self.addr, number))
