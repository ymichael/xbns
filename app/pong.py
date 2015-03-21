import argparse
import datetime
import net.layers.application
import net.layers.base
import net.radio.xbeeradio
import serial
import struct
import threading
import time
import utils.cli
import utils.git
import utils.pdu
import utils.timespec
import xbee


class Message(utils.pdu.PDU):
    TYPES = [
        "PING",         # Simple message to check liveness.
        "PONG",         # Response for liveness check.
        "TIME_REQ",     # Request time from neighbours.
        "TIME_SET",     # Sends current time to neighbours.
        "PL_SET",       # Set power level

        # Topology related messages.
        # 1. To get neighbours, node sends a TOPO_PING and keep tracks of the number
        #    of TOPO_PONG(s) received from various nodes.
        # 2. To get network topology, initiate a TOPO_FLOOD, which causes each node to
        #    perform a TOPO_PING, receive local information about neighbours then
        #    flood the network with this information.
        # 3. To get a particular node's topology information, send a TOPO_REQ.
        "TOPO_REQ",     # Requests for topology information.
        "TOPO_RES",     # Response for topology information.
        "TOPO_FLOOD",   # Flood network with messages about local topology.
        "TOPO_PING",    # Broadcasts a ping to get neighbour information.
        "TOPO_PONG",    # Responds to neighbours TOPO_PING

        # Make command. Runs a makefile target remotely.
        "MAKE",
    ]

    TIME_FORMAT = "HBBBBBH"
    TIME_FORMAT_SIZE = struct.calcsize(TIME_FORMAT)
    REV_SIZE = 7 # `git rev-parse --short HEAD`
    PL_FORMAT = "H"
    TOPO_PONG_FORMAT = "H"

    def _init_pong(self):
        tfs = self.TIME_FORMAT_SIZE
        crs = self.REV_SIZE
        self.time_tuple = self.message[:tfs]
        self.time_tuple = struct.unpack(self.TIME_FORMAT, self.time_tuple)
        self.current_rev = self.message[tfs:tfs + crs]
        self.addition_msg = self.message[tfs + crs:]

    def _init_topo_pong(self):
        self.recipient_addr = \
            struct.unpack(self.TOPO_PONG_FORMAT, self.message)[0]

    def _init_topo_res(self):
        self.neighbours = \
            struct.unpack('B' * len(self.message), self.message)

    def _init_time_set(self):
        self.time_tuple = struct.unpack(self.TIME_FORMAT, self.message)

    def _init_pl_set(self):
        self.power_level = struct.unpack(self.PL_FORMAT, self.message)[0]

    def _init_make(self):
        self.target = self.message

    def _repr_topo_pong(self):
        return "%6s, %s" % (self.type, self.recipient_addr)

    def _repr_topo_res(self):
        return "%6s, %s" % (self.type, self.neighbours)

    def _repr_pong(self):
        return "%6s, %s, %s, %s" % \
            (self.type, self.time_tuple, self.current_rev, self.addition_msg)

    def _repr_make(self):
        return "%6s, %s" % (self.type, self.message)

    def _repr_time_set(self):
        return "%6s, %s" % (self.type, self.time_tuple)

    @classmethod
    def create_pl_set(cls, pl):
        assert 0 <= pl <= 4
        message = struct.pack(cls.PL_FORMAT, pl)
        return cls(cls.PL_SET, message)

    @classmethod
    def create_pong(cls, time_tuple, current_revision, addition_msg=""):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        # Strip newlines from addition_msg
        addition_msg = addition_msg.replace("\n", ", ")
        return cls(cls.PONG, message + current_revision + addition_msg)

    @classmethod
    def create_time_set(cls, time_tuple):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        return cls(cls.TIME_SET, message)

    @classmethod
    def create_topo_res(cls, neighbours):
        message = struct.pack("B" * len(neighbours), *neighbours)
        return cls(cls.TOPO_RES, message)

    @classmethod
    def create_topo_pong(cls, recipient_addr):
        message = struct.pack(cls.TOPO_PONG_FORMAT, recipient_addr)
        return cls(cls.TOPO_PONG, message)

    @classmethod
    def create_make(cls, target):
        return cls(cls.MAKE, target)


class Mode(object):
    # The normal mode that the nodes run in.
    NORMAL = 'normal'

    # Utility modes that help ease management of the nodes.
    PING = 'ping'
    TIME = 'time'
    POWER = 'power'

    # TOPO mode: Get topology information about nodes.
    TOPO_REQ = 'toporeq'
    TOPO_FLOOD = 'topoflood'

    MAKE = 'make'


class Pong(net.layers.application.Application):
    """Collection of utilities for managing the Beaglebone."""
    ADDRESS = ("", 11004)

    TIME_REQ_MAX_RETRIES = 5

    def __init__(self, addr):
        super(Pong, self).__init__(addr)
        self.mode = None
        self.rev = utils.git.get_current_revision()
        self.xbee = None
        self.topo_pongs = {}

        # Time set.
        self._time_is_set = False
        self._time_reqs_sent = 0
        self._time_req_timer = None

        # Timers
        self._topo_res_timer = None
        self._topo_flood_timer = None

    def set_xbee(self, xbee):
        self.xbee = xbee

    def set_mode(self, mode):
        self.mode = mode
        if self.mode is Mode.NORMAL:
            self.start_normal()

    def set_rev(self, rev):
        self.rev = rev

    def start_normal(self):
        time.sleep(10)
        self.send_time_req_delayed()

    def _handle_incoming_message(self, message, sender_addr):
        message = Message.from_string(message)
        self.log("Received message from %s: %s" % (sender_addr, repr(message)))

        # TOPO related messages.
        if message.is_topo_req():
            self.send_topo_res_delayed()
            self.send_topo_ping()

        if message.is_topo_flood():
            self.send_topo_flood_res_delayed()
            self.send_topo_ping()

        if message.is_topo_ping():
            self.send_topo_pong(sender_addr)

        if message.is_topo_pong() and message.recipient_addr == self.addr:
            self.topo_pongs[(time.time(), sender_addr)] = sender_addr

        # Only set time in NORMAL mode.
        if message.is_time_set():
            utils.timespec.TimeSpec.set_time(message.time_tuple)
            self._time_is_set = True
            self.send_pong_flood()

        if message.is_time_req():
            self.send_time_set()

        if message.is_ping():
            self.send_pong()

        if message.is_pl_set():
            if self.xbee is not None:
                self.xbee.set_power_level(message.power_level)
            self.send_pong()

        if message.is_make() and self.mode != Mode.MAKE:
            output = utils.cli.call(["make", message.target])
            self.send_pong(addition_msg=output[:50], dest_addr=sender_addr)

    def _get_neighbours(self):
        # Determine neighbours
        curr_t = time.time()
        for k in self.topo_pongs.keys():
            t, addr = k
            if (curr_t - t) > 1.5:
                del self.topo_pongs[k]
        return set(self.topo_pongs.values())

    def send_topo_req(self):
        topo_req = Message.create_topo_req()
        self._send_message(topo_req)

    def send_topo_flood(self):
        topo_flood = Message.create_topo_flood()
        self._send_message(topo_flood, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def send_topo_res_delayed(self):
        if self._topo_res_timer is not None:
            self._topo_res_timer.cancel()
        self._topo_res_timer = threading.Timer(.5, self.send_topo_res)
        self._topo_res_timer.start()

    def send_topo_res(self):
        time.sleep(.5)
        topo_res = Message.create_topo_res(self._get_neighbours())
        self._send_message(topo_res)

    def send_topo_flood_res_delayed(self):
        if self._topo_res_timer is not None:
            self._topo_res_timer.cancel()
        self._topo_res_timer = threading.Timer(.5, self.send_topo_flood_res)
        self._topo_res_timer.start()

    def send_topo_flood_res(self):
        time.sleep(.5)
        topo_res = Message.create_topo_res(self._get_neighbours())
        self._send_message(topo_res, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def send_time_req_delayed(self):
        if self._time_req_timer is not None:
            self._time_req_timer.cancel()
        self._time_req_timer = threading.Timer(5, self.send_time_req)
        self._time_req_timer.start()

    def send_time_req(self):
        if self._time_is_set:
            return
        self._time_reqs_sent += 1
        time_req = Message.create_time_req()
        self._send_message(time_req)

        if self._time_reqs_sent < self.TIME_REQ_MAX_RETRIES:
            self.send_time_req_delayed()

    def send_topo_pong(self, addr):
        topo_pong = Message.create_topo_pong(addr)
        self._send_message(topo_pong)

    def send_topo_ping(self):
        topo_ping = Message.create_topo_ping()
        self._send_message(topo_ping)

    def send_ping(self):
        ping = Message.create_ping()
        self._send_message(ping)

    def send_pong(self, addition_msg="", dest_addr=None):
        time_tuple = utils.timespec.TimeSpec.get_current_time()
        current_rev = utils.git.get_current_revision()
        pong = Message.create_pong(
            time_tuple, current_rev, addition_msg=addition_msg)
        self._send_message(pong, dest_addr=dest_addr)

    def send_pong_flood(self, addition_msg=""):
        self.send_pong(
            addition_msg=addition_msg,
            dest_addr=net.layers.base.FLOOD_ADDRESS)

    def send_time_set(self):
        time_set = Message.create_time_set(
            utils.timespec.TimeSpec.get_current_time())
        self._send_message(time_set, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def send_pl_set(self, value):
        pl_set = Message.create_pl_set(value)
        self._handle_incoming_inner(pl_set)
        self._send_message(pl_set)

    def send_make_flood(self, target):
        make = Message.create_make(target)
        self._send_message(make, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def _send_message(self, message, dest_addr=None):
        self._send(message.to_string(), dest_addr=dest_addr)
        self.log("Sending message (%s): %s" % (len(message.to_string()), repr(message)))


def main(args):
    serial_object = serial.Serial(args.port, args.baudrate)
    xbee_module = xbee.XBee(serial_object, escaped=True)
    xbee_radio = net.radio.xbeeradio.XBeeRadio(xbee_module)

    app = Pong.create_and_run_application()
    app.set_mode(args.mode)
    app.set_rev(args.rev or utils.git.get_current_revision())
    app.set_xbee(xbee_radio)

    once = True
    while True:
        if args.mode == Mode.PING:
            app.send_ping()
            time.sleep(1)

        if args.mode == Mode.TIME:
            app.send_time_set()
            time.sleep(5)

        if args.mode == Mode.POWER:
            if once:
                app.send_pl_set(args.value)
                once = False
            else:
                app.send_ping()
            time.sleep(1)

        if args.mode == Mode.TOPO_REQ:
            app.send_topo_req()
            time.sleep(1)

        if args.mode == Mode.TOPO_FLOOD:
            app.send_topo_flood()
            time.sleep(2)

        if once and args.mode == Mode.MAKE:
            assert args.target
            once = False
            app.send_make_flood(args.target)

        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pong Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL,
                        choices=[Mode.NORMAL, Mode.PING, Mode.TIME, Mode.POWER,
                            Mode.TOPO_REQ, Mode.TOPO_FLOOD, Mode.MAKE])
    # Power Level.
    parser.add_argument('--value', type=int, default=4, choices=[0,1,2,3,4])
    # XBee configuration
    parser.add_argument('-s', '--port', default='/dev/ttyUSB0',
                        help='Serial port')
    parser.add_argument('-b', '--baudrate', default=57600, type=int,
                        help='Baudrate')
    # Make mode.
    parser.add_argument("--target", type=str,
                        help="Makefile target to remotely execute in network.")
    args = parser.parse_args()
    main(args)
