import argparse
import ctypes
import ctypes.util
import datetime
import net.layers.application
import net.layers.base
import net.layers.transport
import struct
import time


class TimeSpec(ctypes.Structure):
    # Source: http://stackoverflow.com/a/12292874/1070617
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

    @staticmethod
    def get_current_time():
        current_time = datetime.datetime.now()
        current_milliseconds = current_time.microsecond / 1000
        time_tuple = current_time.timetuple()[:6] + (current_milliseconds,)
        return time_tuple

    @staticmethod
    def set_time(time_tuple):
        librt = ctypes.CDLL(ctypes.util.find_library("rt"))
        ts = TimeSpec()
        ts.tv_sec = int(time.mktime(datetime.datetime(*time_tuple[:6]).timetuple()))
        ts.tv_nsec = time_tuple[6] * 1000000
        librt.clock_settime(0, ctypes.byref(ts))


class Message(object):
    HEADER_PREFIX = "B"
    HEADER_PREFIX_SIZE = struct.calcsize(HEADER_PREFIX)

    PING =       0  # Simple message to check liveness.
    PONG =       1  # Response for liveness check.
    TIME_REQ =   2  # Request time from neighbours.
    TIME_SET =   3  # Sends current time to neighbours.
    PL_SET =     4  # Set power level

    # Topology related messages.
    # 1. To get neighbours, node sends a TOPO_PING and keep tracks of the number
    #    of TOPO_PONG(s) received from various nodes.
    # 2. To get network topology, initiate a TOPO_POLL, which causes each node to
    #    perform a TOPO_PING, receive local information about neighbours then
    #    broadcast a TOPO_FLOOD with this information.
    # 3. To get a particular node's topology information, send a TOPO_REQ.
    TOPO_POLL =  5  # Initiates TOPO_FLOOD
    TOPO_REQ =   6  # Requests for topology information.
    TOPO_FLOOD = 7  # Flood network with messages about local topology.
    TOPO_PING =  8  # Broadcasts a ping to get neighbour information.
    TOPO_PONG =  9  # Responds to neighbours TOPO_PING

    TIME_FORMAT = "HBBBBBH"
    PL_FORMAT = "H"

    def __init__(self, msg_type, message):
        self.msg_type = msg_type
        self.message = message

        if self.is_pong():
            self._init_pong()
        if self.is_time_set():
            self._init_time_set()
        if self.is_pl_set():
            self._init_pl_set()

    def _init_pong(self):
        self.time_tuple = struct.unpack(self.TIME_FORMAT, self.message)

    def _init_time_set(self):
        self.time_tuple = struct.unpack(self.TIME_FORMAT, self.message)

    def _init_pl_set(self):
        self.power_level = struct.unpack(self.PL_FORMAT, self.message)[0]

    def is_ping(self):
        return self.msg_type == self.PING

    def is_pong(self):
        return self.msg_type == self.PONG

    def is_time_req(self):
        return self.msg_type == self.TIME_REQ

    def is_time_set(self):
        return self.msg_type == self.TIME_SET

    def is_pl_set(self):
        return self.msg_type == self.PL_SET

    def is_topo_poll(self):
        return self.msg_type == self.TOPO_POLL

    def is_topo_req(self):
        return self.msg_type == self.TOPO_REQ

    def is_topo_flood(self):
        return self.msg_type == self.TOPO_FLOOD

    def is_topo_ping(self):
        return self.msg_type == self.TOPO_PING

    def is_topo_pong(self):
        return self.msg_type == self.TOPO_PONG

    @property
    def type(self):
        if self.is_ping(): return 'PING'
        if self.is_pong(): return 'PONG'
        if self.is_time_req(): return 'TIME_REQ'
        if self.is_time_set(): return 'TIME_SET'
        if self.is_pl_set(): return 'PL_SET'
        if self.is_topo_poll(): return 'TOPO_POLL'
        if self.is_topo_req(): return 'TOPO_REQ'
        if self.is_topo_flood(): return 'TOPO_FLOOD'
        if self.is_topo_ping(): return 'TOPO_PING'
        if self.is_topo_pong(): return 'TOPO_PONG'

    def __repr__(self):
        if self.is_pong(): return self._repr_pong()
        if self.is_time_set(): return self._repr_time_set()
        return "%6s" % self.type

    def _repr_pong(self):
        return "%6s, %s" % (self.type, self.time_tuple)

    def _repr_time_set(self):
        return "%6s, %s" % (self.type, self.time_tuple)

    def to_string(self):
        header = struct.pack(self.HEADER_PREFIX, self.msg_type)
        return header + self.message

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_PREFIX, data[:cls.HEADER_PREFIX_SIZE])
        return cls(x[0], data[cls.HEADER_PREFIX_SIZE:])

    @classmethod
    def create_ping(cls):
        return cls(cls.PING, "")

    @classmethod
    def create_time_req(cls):
        return cls(cls.TIME_REQ, "")

    @classmethod
    def create_pl_set(cls, pl):
        assert 0 <= pl <= 4
        message = struct.pack(cls.PL_FORMAT, pl)
        return cls(cls.PL_SET, message)

    @classmethod
    def create_pong(cls, time_tuple):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        return cls(cls.PONG, message)

    @classmethod
    def create_time_set(cls, time_tuple):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        return cls(cls.TIME_SET, message)

    @classmethod
    def create_topo_poll(cls):
        return cls(cls.TOPO_POLL, "")

    @classmethod
    def create_topo_req(cls):
        return cls(cls.TOPO_REQ, "")

    @classmethod
    def create_topo_flood(cls):
        return cls(cls.TOPO_FLOOD, "")

    @classmethod
    def create_topo_ping(cls):
        return cls(cls.TOPO_PING, "")

    @classmethod
    def create_topo_pong(cls):
        return cls(cls.TOPO_PONG, "")


class Mode(object):
    NORMAL = 'normal'
    PING = 'ping'
    TIME = 'time'
    POWER = 'power'


class Pong(net.layers.application.Application):
    """Collection of utilities for managing the Beaglebone."""
    ADDRESS = ("", 11004)

    def __init__(self, addr):
        super(Pong, self).__init__(addr)
        self.mode = None
        self.xbee = None

    def set_xbee(self, xbee):
        self.xbee = xbee

    def set_mode(self, mode):
        self.mode = mode

    def _handle_incoming(self, data):
        pdu = net.layers.transport.TransportPDU.from_string(data)
        message = Message.from_string(pdu.message)
        self.log("Received message from %3s: %s" % (pdu.source_addr, repr(message)))
        self._handle_incoming_inner(message)

    def _handle_incoming_inner(self, message):
        # Only handle incoming messages when run in normal mode.
        if self.mode != Mode.NORMAL:
            return

        if message.is_time_set():
            TimeSpec.set_time(message.time_tuple)
            self.send_pong()

        if message.is_time_req():
            self.send_time_set()

        if message.is_ping():
            self.send_pong()

        if message.is_pl_set():
            if self.xbee is not None:
                self.xbee.set_power_level(message.power_level)
            self.send_pong()

    def send_ping(self):
        ping = Message.create_ping()
        self._send_message(ping)

    def send_pong(self):
        pong = Message.create_pong(TimeSpec.get_current_time())
        self._send_message(pong)

    def send_time_set(self):
        time_set = Message.create_time_set(TimeSpec.get_current_time())
        self._send_message(time_set, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def send_pl_set(self, value):
        pl_set = Message.create_pl_set(value)
        self._handle_incoming_inner(pl_set)
        self._send_message(pl_set)

    def _send_message(self, message, dest_addr=None):
        self._send(message.to_string(), dest_addr=dest_addr)
        self.log("Sending message (%s): %s" % (len(message.to_string()), repr(message)))


def main(args):
    app = Pong.create_and_run_application()
    app.set_mode(args.mode)

    import serial
    import xbee
    import net.radio.xbeeradio
    serial_object = serial.Serial(args.port, args.baudrate)
    xbee_module = xbee.XBee(serial_object, escaped=True)
    xbee_radio = net.radio.xbeeradio.XBeeRadio(xbee_module)
    app.set_xbee(xbee_radio)

    once = True

    while True:
        if args.mode == Mode.PING:
            app.send_ping()
            time.sleep(1)
        elif args.mode == Mode.TIME:
            app.send_time_set()
            time.sleep(5)
        elif args.mode == Mode.POWER:
            if once:
                app.send_pl_set(args.value)
                once = False
            else:
                app.send_ping()
            time.sleep(1)

        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pong Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL,
                        choices=[Mode.NORMAL, Mode.PING, Mode.TIME, Mode.POWER])
    parser.add_argument('--value', type=int, default=4, choices=[0,1,2,3,4])
    parser.add_argument('-s', '--port', default='/dev/ttyUSB0',
                        help='Serial port')
    parser.add_argument('-b', '--baudrate', default=57600, type=int,
                        help='Baudrate')
    args = parser.parse_args()
    main(args)
