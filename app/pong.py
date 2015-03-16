import argparse
import datetime
import net.layers.application
import net.layers.base
import net.layers.transport
import net.radio.xbeeradio
import serial
import struct
import threading
import time
import utils.cli
import utils.git
import xbee

from utils.timespec import TimeSpec


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
    # 2. To get network topology, initiate a TOPO_FLOOD, which causes each node to
    #    perform a TOPO_PING, receive local information about neighbours then
    #    flood the network with this information.
    # 3. To get a particular node's topology information, send a TOPO_REQ.
    TOPO_REQ =   6  # Requests for topology information.
    TOPO_RES =   7  # Response for topology information.
    TOPO_FLOOD = 8  # Flood network with messages about local topology.
    TOPO_PING =  9  # Broadcasts a ping to get neighbour information.
    TOPO_PONG =  10  # Responds to neighbours TOPO_PING

    # Upgrade related messages.
    # - To initiate upgrade, start Pong app in Mode.UPGRADE mode.
    # 1. This sends out a UPGRADE_FLOOD message with the current revision.
    # 2. Upon receiving this UPGRADE_FLOOD message, nodes check if they are
    #    behind or ahead of this advertised revision.
    # 3. If a node is ahead, ignore message and respond with a PING.
    # 4. If the node is behind, send an UPGRADE_REQ message with its current revision.
    # 5. Only the node with in UPGRADE mode will respond to UPGRADE_REQs with UPGRADE_PATCH
    #    which contain the git patches to upgrade.
    # 6. Once a node is up-to-date, it responds with a PING
    UPGRADE_FLOOD = 11
    UPGRADE_REQ = 12
    UPGRADE_PATCH = 13

    # Make command. Runs a makefile target remotely.
    MAKE = 14

    TIME_FORMAT = "HBBBBBH"
    TIME_FORMAT_SIZE = struct.calcsize(TIME_FORMAT)
    REV_SIZE = 7 # `git rev-parse --short HEAD`
    PL_FORMAT = "H"
    TOPO_PONG_FORMAT = "H"

    def __init__(self, msg_type, message):
        self.msg_type = msg_type
        self.message = message
        if self.is_pong(): self._init_pong()
        if self.is_time_set(): self._init_time_set()
        if self.is_pl_set(): self._init_pl_set()
        if self.is_topo_pong(): self._init_topo_pong()
        if self.is_topo_res(): self._init_topo_res()
        if self.is_upgrade_flood(): self._init_upgrade_flood()
        if self.is_upgrade_req(): self._init_upgrade_req()
        if self.is_upgrade_patch(): self._init_upgrade_patch()
        if self.is_make(): self._init_make()

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

    def _init_upgrade_flood(self):
        self.rev = self.message

    def _init_upgrade_req(self):
        self.rev = self.message

    def _init_upgrade_patch(self):
        self.from_rev = self.message[:self.REV_SIZE]
        self.to_rev = self.message[self.REV_SIZE:2 * self.REV_SIZE]
        self.patch = self.message[2 * self.REV_SIZE:]

    def _init_make(self):
        self.target = self.message

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

    def is_topo_req(self):
        return self.msg_type == self.TOPO_REQ

    def is_topo_res(self):
        return self.msg_type == self.TOPO_RES

    def is_topo_flood(self):
        return self.msg_type == self.TOPO_FLOOD

    def is_topo_ping(self):
        return self.msg_type == self.TOPO_PING

    def is_topo_pong(self):
        return self.msg_type == self.TOPO_PONG

    def is_upgrade_flood(self):
        return self.msg_type == self.UPGRADE_FLOOD

    def is_upgrade_req(self):
        return self.msg_type == self.UPGRADE_REQ

    def is_upgrade_patch(self):
        return self.msg_type == self.UPGRADE_PATCH

    def is_make(self):
        return self.msg_type == self.MAKE

    @property
    def type(self):
        if self.is_ping(): return 'PING'
        if self.is_pong(): return 'PONG'
        if self.is_time_req(): return 'TIME_REQ'
        if self.is_time_set(): return 'TIME_SET'
        if self.is_pl_set(): return 'PL_SET'
        if self.is_topo_req(): return 'TOPO_REQ'
        if self.is_topo_res(): return 'TOPO_RES'
        if self.is_topo_flood(): return 'TOPO_FLOOD'
        if self.is_topo_ping(): return 'TOPO_PING'
        if self.is_topo_pong(): return 'TOPO_PONG'
        if self.is_upgrade_flood(): return 'UPGRADE_FLOOD'
        if self.is_upgrade_req(): return 'UPGRADE_REQ'
        if self.is_upgrade_patch(): return 'UPGRADE_PATCH'
        if self.is_make(): return 'MAKE'

    def __repr__(self):
        if self.is_pong(): return self._repr_pong()
        if self.is_time_set(): return self._repr_time_set()
        if self.is_topo_pong(): return self._repr_topo_pong()
        if self.is_topo_res(): return self._repr_topo_res()
        if self.is_upgrade_flood(): return self._repr_upgrade_flood()
        if self.is_upgrade_req(): return self._repr_upgrade_req()
        if self.is_upgrade_patch(): return  self._repr_upgrade_patch()
        if self.is_make(): return  self._repr_make()
        return "%6s" % self.type

    def _repr_upgrade_flood(self):
        return "%s, current_rev = %s" % (self.type, self.rev)

    def _repr_upgrade_req(self):
        return "%s, current_rev = %s" % (self.type, self.rev)

    def _repr_upgrade_patch(self):
        return "%s, from_rev = %s, to_rev = %s, size = %s" % \
            (self.type, self.from_rev, self.to_rev, len(self.patch))

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
    def create_pong(cls, time_tuple, current_revision, addition_msg=""):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        return cls(cls.PONG, message + current_revision + addition_msg)

    @classmethod
    def create_time_set(cls, time_tuple):
        message = struct.pack(cls.TIME_FORMAT, *time_tuple)
        return cls(cls.TIME_SET, message)

    @classmethod
    def create_topo_req(cls):
        return cls(cls.TOPO_REQ, "")

    @classmethod
    def create_topo_res(cls, neighbours):
        message = struct.pack("B" * len(neighbours), *neighbours)
        return cls(cls.TOPO_RES, message)

    @classmethod
    def create_topo_flood(cls):
        return cls(cls.TOPO_FLOOD, "")

    @classmethod
    def create_topo_ping(cls):
        return cls(cls.TOPO_PING, "")

    @classmethod
    def create_topo_pong(cls, recipient_addr):
        message = struct.pack(cls.TOPO_PONG_FORMAT, recipient_addr)
        return cls(cls.TOPO_PONG, message)

    @classmethod
    def create_upgrade_flood(cls, rev):
        return cls(cls.UPGRADE_FLOOD, rev)

    @classmethod
    def create_upgrade_req(cls, rev):
        return cls(cls.UPGRADE_REQ, rev)

    @classmethod
    def create_upgrade_patch(cls, from_rev, to_rev, patch):
        return cls(cls.UPGRADE_PATCH, "".join([from_rev, to_rev, patch]))

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

    # Upgrade mode: Request and send git patches to nodes.
    UPGRADE = 'upgrade'
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

        # Other states
        self._sent_upgrade_patches = {}

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

    def _handle_incoming(self, data):
        pdu = net.layers.transport.TransportPDU.from_string(data)
        message = Message.from_string(pdu.message)
        self.log("Received message from %3s: %s" % (pdu.source_addr, repr(message)))
        self._handle_incoming_inner(message, pdu.source_addr)

    def _handle_incoming_inner(self, message, sender_addr):
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
            TimeSpec.set_time(message.time_tuple)
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

        # UPGRADE related messages.
        if message.is_upgrade_flood() and self.mode != Mode.UPGRADE:
            if utils.git.has_revision(message.rev):
                self.send_pong(dest_addr=sender_addr)
            else:
                self.send_upgrade_req(dest_addr=sender_addr)

        if message.is_upgrade_patch() and self.mode == Mode.NORMAL:
            # Check if patch is applicable for this node.
            if message.from_rev == utils.git.get_current_revision():
                output = utils.git.apply_patch(message.patch)
                self.log("Applying Patch: %s" % output)
                self.send_pong(addition_msg=output[:20], dest_addr=sender_addr)
                self.restart_and_reload_processes()

        if message.is_upgrade_req() and self.mode == Mode.UPGRADE:
            # Check if we've sent the patch before
            # TODO: Check the time since sent, perhaps resend after x secs?
            if (message.rev, self.rev) in self._sent_upgrade_patches:
                return
            patch = utils.git.get_patch_for_revision(from_rev=message.rev, to_rev=self.rev)
            upgrade_patch = Message.create_upgrade_patch(
                from_rev=message.rev, to_rev=self.rev, patch=patch)
            self._sent_upgrade_patches[(message.rev, self.rev)] = datetime.datetime.now()
            self._send_message(upgrade_patch, dest_addr=net.layers.base.FLOOD_ADDRESS)

        if message.is_make() and self.mode != Mode.NORMAL:
            output = utils.cli.call(["make", message.target])
            self.send_pong(addition_msg=output[:20], dest_addr=sender_addr)

    def restart_and_reload_processes(self):
        # Restart manager and xbns.
        utils.cli.call(["make", "restart"])
        # TODO. reload pong app/modules loaded.

    def send_upgrade_req(self, dest_addr):
        current_rev = utils.git.get_current_revision()
        upgrade_req = Message.create_upgrade_req(current_rev)
        self._send_message(upgrade_req, dest_addr=dest_addr)

    def send_upgrade_flood(self):
        upgrade_flood = Message.create_upgrade_flood(self.rev)
        self._send_message(upgrade_flood, dest_addr=net.layers.base.FLOOD_ADDRESS)

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
        time_tuple = TimeSpec.get_current_time()
        current_rev = utils.git.get_current_revision()
        pong = Message.create_pong(
            time_tuple, current_rev, addition_msg=addition_msg)
        self._send_message(pong, dest_addr=dest_addr)

    def send_pong_flood(self, addition_msg=""):
        self.send_pong(
            addition_msg=addition_msg,
            dest_addr=net.layers.base.FLOOD_ADDRESS)

    def send_time_set(self):
        time_set = Message.create_time_set(TimeSpec.get_current_time())
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

        if once and args.mode == Mode.UPGRADE:
            once = False
            app.send_upgrade_flood()

        if once and args.mode == Mode.MAKE:
            assert args.target
            once = False
            app.send_make_flood(args.target)

        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pong Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL,
                        choices=[Mode.NORMAL, Mode.PING, Mode.TIME, Mode.POWER,
                            Mode.TOPO_REQ, Mode.TOPO_FLOOD, Mode.UPGRADE, Mode.MAKE])
    # Power Level.
    parser.add_argument('--value', type=int, default=4, choices=[0,1,2,3,4])
    # XBee configuration
    parser.add_argument('-s', '--port', default='/dev/ttyUSB0',
                        help='Serial port')
    parser.add_argument('-b', '--baudrate', default=57600, type=int,
                        help='Baudrate')
    # Upgrade mode.
    parser.add_argument("--rev", type=str, help="Revision to upgrade to.")
    # Make mode.
    parser.add_argument("--target", type=str,
                        help="Makefile target to remotely execute in network.")
    args = parser.parse_args()
    main(args)
