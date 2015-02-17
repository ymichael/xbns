import argparse
import ctypes
import ctypes.util
import datetime
import net.layers.application
import net.layers.transport
import ping
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

    PING = 0
    PONG = 1
    TIME_REQ = 2
    TIME_SET = 3

    TIME_FORMAT = "HBBBBBH"

    def __init__(self, msg_type, message):
        self.msg_type = msg_type
        self.message = message

        if self.is_ping():
            self._init_ping()
        elif self.is_pong():
            self._init_pong()
        elif self.is_time_req():
            self._init_time_req()
        elif self.is_time_set():
            self._init_time_set()

    def _init_ping(self):
        pass

    def _init_pong(self):
        self.time_tuple = struct.unpack(self.TIME_FORMAT, self.message)

    def _init_time_req(self):
        pass

    def _init_time_set(self):
        self.time_tuple = struct.unpack(self.TIME_FORMAT, self.message)

    def is_ping(self):
        return self.msg_type == self.PING

    def is_pong(self):
        return self.msg_type == self.PONG

    def is_time_req(self):
        return self.msg_type == self.TIME_REQ

    def is_time_set(self):
        return self.msg_type == self.TIME_SET

    @property
    def type(self):
        if self.is_ping():
            return 'PING'
        elif self.is_pong():
            return 'PONG'
        elif self.is_time_req():
            return 'TIME_REQ'
        elif self.is_time_set():
            return 'TIME_SET'

    def __repr__(self):
        if self.is_ping():
            return self._repr_ping()
        elif self.is_pong():
            return self._repr_pong()
        elif self.is_time_req():
            return self._repr_time_req()
        elif self.is_time_set():
            return self._repr_time_set()

    def _repr_ping(self):
        return "%6s" % self.type

    def _repr_pong(self):
        return "%6s, %s" % (self.type, self.time_tuple)

    def _repr_time_req(self):
        return "%6s" % self.type

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
    def create_pong(cls, time_tuple):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        return cls(cls.PONG, message)

    @classmethod
    def create_time_set(cls, time_tuple):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        return cls(cls.TIME_SET, message)


class Mode(object):
    NORMAL = 'normal'
    PING = 'ping'
    TIME = 'time'


class Pong(net.layers.application.Application):
    """Collection of utilities for managing the Beaglebone."""
    ADDRESS = ("", 11004)

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

        if message.is_ping():
            self.send_pong()

    def send_ping(self):
        ping = Message.create_ping()
        self._send_message(ping)

    def send_pong(self):
        pong = Message.create_pong(TimeSpec.get_current_time())
        self._send_message(pong)

    def send_time_set(self):
        time_set = Message.create_time_set(TimeSpec.get_current_time())
        self._send_message(time_set)

    def _send_message(self, message):
        self.send(message.to_string())
        self.log("Sending message (%s): %s" % (len(message.to_string()), repr(message)))


def main(args):
    app = Pong.create_and_run_application()
    app.set_mode(args.mode)
    while True:
        if args.mode == Mode.PING:
            app.send_ping()
            time.sleep(1)
        elif args.mode == Mode.TIME:
            app.send_time_set()
            time.sleep(5)
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pong Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL,
                        choices=[Mode.NORMAL, Mode.PING, Mode.TIME])
    args = parser.parse_args()
    main(args)
