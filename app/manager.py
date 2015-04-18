import app.deluge
import app.protocol.rateless_deluge
import app.rateless_deluge
import argparse
import net.layers.application
import net.layers.base
import pickle
import struct
import threading
import time
import utils.pdu


class Protocol(object):
    DELUGE = 0
    RATELESS = 1
    NAMES = ["deluge", "rateless"]

    @classmethod
    def get_protocol(cls, string):
        return cls.NAMES.index(string)

    @classmethod
    def get_name(cls, protocol):
        return cls.NAMES[protocol]


class Mode(object):
    # Run the protocols normally with the given parameters.
    NORMAL = "NORMAL"
    # Update already running protocols to the given parameters (OTA).
    CONTROL = "CONTROL"
    # Listen mode, don't interupt current protocol.
    LISTEN = "LISTEN"
    # Ping mode, force send ADV.
    PING = "PING"


class ManagerPDU(utils.pdu.PDU):
    TYPES = ["ACK", "CTRL", "PING"]

    def _init_ctrl(self):
        x = pickle.loads(self.message)
        self.protocol = x[0]
        self.d_page_size = x[1]
        self.d_packet_size = x[2]
        self.r_page_size = x[3]
        self.r_packet_size = x[4]
        self.k = x[5]
        self.t_min = x[6]
        self.t_max = x[7]
        self.delay = x[8]
        self.frame_delay = x[9]
        self.t_r = x[10]
        self.t_tx = x[11]
        self.w = x[12]
        self.rx_max = x[13]

    def _repr_ctrl(self):
        format = "%4s, %s, d = %s/%s, r = %s/%s k = %s, t_min = %s, t_max = %s, " + \
            "delay = %s, frame_delay = %s, t_r = %s, t_tx = %s, w = %s, rx_max = %s"
        return format % (self.type, Protocol.get_name(self.protocol),
            self.d_page_size, self.d_packet_size,
            self.r_page_size, self.r_packet_size,
            self.k, self.t_min, self.t_max, self.delay, self.frame_delay,
            self.t_r, self.t_tx, self.w, self.rx_max)

    @classmethod
    def create_ctrl(cls,
            protocol=Protocol.DELUGE,
            d_page_size=1020,
            d_packet_size=60,
            r_page_size=900,
            r_packet_size=45,
            k=1,
            t_min=1,
            t_max=60 * 10,
            delay=5,
            frame_delay=.02,
            t_r=.5,
            t_tx=.2,
            w=10,
            rx_max=2):
        assert d_page_size % d_packet_size == 0
        assert r_page_size % r_packet_size == 0
        assert t_min <= t_max
        assert protocol < len(Protocol.NAMES)
        message = pickle.dumps([
            protocol,
            d_page_size,
            d_packet_size,
            r_page_size,
            r_packet_size,
            k,
            t_min,
            t_max,
            delay,
            frame_delay,
            t_r,
            t_tx,
            w,
            rx_max,
        ])
        return cls(cls.CTRL, message)


class Manager(net.layers.application.Application):
    """Run and manage both rateless and deluge concurrently."""
    ADDRESS = ("", 11006)

    # Parameters
    PROTOCOL = Protocol.DELUGE

    D_PAGE_SIZE = 1020
    D_PACKET_SIZE = 60
    D_PACKETS_PER_PAGE = D_PAGE_SIZE / D_PACKET_SIZE

    R_PAGE_SIZE = 900
    R_PACKET_SIZE = 45
    R_PACKETS_PER_PAGE = R_PAGE_SIZE / R_PACKET_SIZE

    K = 1
    T_MIN = 1
    T_MAX = 60 * 10
    DELAY = 5
    FRAME_DELAY = .02
    T_R = .5
    T_TX = .2
    W = 10
    RX_MAX = 2

    def __init__(self, addr):
        super(Manager, self).__init__(addr)
        self.apps = {}
        self._create_protocol_applications()
        self.deluge.stop_protocol()
        self.rateless.stop_protocol()
        self._start_timer = None

        # Used to ensure that all nodes in the network received the CTRL/PING
        # messages.
        self.nodes = None
        self.heard_from = set()

    def _create_protocol_applications(self):
        self.apps[Protocol.DELUGE] = app.deluge.Deluge.create_and_run_application()
        self.apps[Protocol.RATELESS] = \
            app.rateless_deluge.RatelessDeluge.create_and_run_application()

    def set_mode(self, mode):
        self.mode = mode

    def set_nodes(self, nodes):
        if nodes is None:
            return
        self.nodes = set(nodes)
        if self.addr in self.nodes:
            self.nodes.remove(self.addr)

    @property
    def deluge(self):
        return self.apps.get(Protocol.DELUGE)

    @property
    def rateless(self):
        return self.apps.get(Protocol.RATELESS)

    def _handle_incoming_message(self, message, sender_addr):
        data_unit = ManagerPDU.from_string(message)
        self._log_receive_pdu(data_unit, sender_addr)
        if data_unit.is_ack():
            self.heard_from.add(sender_addr)
        if data_unit.is_ctrl():
            self._send_ack(sender_addr)
            self._process_ctrl(data_unit)
        if data_unit.is_ping():
            self._send_ack(sender_addr)
            self._process_ping()

    def _process_ping(self):
        # Get active protocol to send ADV is in normal mode.
        if self.mode == Mode.NORMAL:
            active = self.apps[self.PROTOCOL]
            active.protocol._send_adv(force=True)

    def _process_ctrl(self, data_unit):
        self._update_ctrl_parameters(data_unit)
        if self.mode == Mode.NORMAL:
            self.delay_start_active(self.DELAY)

    def _update_ctrl_parameters(self, data_unit):
        self.PROTOCOL = data_unit.protocol

        # Deluge
        self.D_PAGE_SIZE = data_unit.d_page_size
        self.D_PACKET_SIZE = data_unit.d_packet_size
        self.D_PACKETS_PER_PAGE = self.D_PAGE_SIZE / self.D_PACKET_SIZE

        # Rateless
        self.R_PAGE_SIZE = data_unit.r_page_size
        self.R_PACKET_SIZE = data_unit.r_packet_size
        self.R_PACKETS_PER_PAGE = self.R_PAGE_SIZE / self.R_PACKET_SIZE

        # Common configuration
        self.K = data_unit.k
        self.T_MIN = data_unit.t_min
        self.T_MAX = data_unit.t_max
        self.DELAY = data_unit.delay
        self.FRAME_DELAY = data_unit.frame_delay
        self.T_R = data_unit.t_r
        self.T_TX = data_unit.t_tx
        self.W = data_unit.w
        self.RX_MAX = data_unit.rx_max

        # Update the two protocols.
        self._update_deluge()
        self._update_rateless()

    def _update_common_config(self, protocol):
        protocol.protocol.T_MIN = self.T_MIN
        protocol.protocol.T_MAX = self.T_MAX
        protocol.protocol.K = self.K
        protocol.protocol.FRAME_DELAY = self.FRAME_DELAY
        protocol.protocol.T_R = self.T_R
        protocol.protocol.T_TX = self.T_TX
        protocol.protocol.W = self.W
        protocol.protocol.RX_MAX = self.RX_MAX

    def _update_deluge(self):
        self.deluge.stop_protocol()
        data = self.deluge.protocol.get_data()
        self.deluge.protocol.PAGE_SIZE = self.D_PAGE_SIZE
        self.deluge.protocol.PACKET_SIZE = self.D_PACKET_SIZE
        self.deluge.protocol.PACKETS_PER_PAGE = self.D_PACKETS_PER_PAGE
        self.deluge.protocol.new_version(1, data, force=True, start=False)
        self._update_common_config(self.deluge)
        self.deluge.protocol._reset_round_state()

    def _update_rateless(self):
        self.rateless.stop_protocol()
        data = self.rateless.protocol.get_data()
        self.rateless.protocol.PAGE_SIZE = self.R_PAGE_SIZE
        self.rateless.protocol.PACKET_SIZE = self.R_PACKET_SIZE
        self.rateless.protocol.PACKETS_PER_PAGE = self.R_PACKETS_PER_PAGE
        self.rateless.protocol.new_version(1, data, force=True, start=False)
        self._update_common_config(self.rateless)
        self.rateless.protocol._reset_round_state()

        app.protocol.rateless_deluge.ROWS_REQUIRED = self.R_PACKETS_PER_PAGE
        self.rateless.protocol.PDU_CLS.DATA_FORMAT = "II" + ("B" * self.R_PACKETS_PER_PAGE) + \
            ("B" * self.R_PACKET_SIZE)

    def start_normal(self, data, version):
        self.delay_start_active(self.DELAY, data, version)

    def delay_start_active(self, delay, data=None, version=None):
        if self._start_timer is not None:
            self._start_timer.cancel()
        self._start_timer = threading.Timer(
            delay, self._start_active, args=(data, version))
        self._start_timer.start()

    def _start_active(self, data, version):
        active = self.apps[self.PROTOCOL]
        active.start_protocol()
        if data or version:
            active.disseminate(data, version)

    def send_ctrl(self):
        if self.nodes is None or not len(self.heard_from):
            self._send_ctrl()
        elif self.nodes == self.heard_from:
            pass # Don't send if all nodes have responsed.
            self.log("All nodes responded.")
        elif float(len(self.heard_from)) / len(self.nodes) < .5:
            # Flood network if heard from less than half the nodes.
            self._send_ctrl()
        else:
            # Send directed packets to each node that has not responded.
            for n in (self.nodes - self.heard_from):
                self._send_ctrl(n)

    def send_ping(self):
        if self.nodes and len(self.nodes) == 1:
            for n in self.nodes:
                self._send_ping(n)
        elif self.nodes is None or not len(self.heard_from):
            self._send_ping()
        elif self.nodes == self.heard_from:
            pass # Don't send if all nodes have responsed.
            self.log("All nodes responded.")
        elif float(len(self.heard_from)) / len(self.nodes) < .5:
            # Flood network if heard from less than half the nodes.
            self._send_ping()
        else:
            # Send directed packets to each node that has not responded.
            for n in (self.nodes - self.heard_from):
                self._send_ping(n)

    def _send_ctrl(self, dest_addr=net.layers.base.FLOOD_ADDRESS):
        ctrl = ManagerPDU.create_ctrl(
            protocol=self.PROTOCOL,
            d_page_size=self.D_PAGE_SIZE,
            d_packet_size=self.D_PACKET_SIZE,
            r_page_size=self.R_PAGE_SIZE,
            r_packet_size=self.R_PACKET_SIZE,
            k=self.K,
            t_min=self.T_MIN,
            t_max=self.T_MAX,
            delay=self.DELAY,
            frame_delay=self.FRAME_DELAY,
            t_r=self.T_R,
            t_tx=self.T_TX,
            w=self.W,
            rx_max=self.RX_MAX)
        self._send_pdu(ctrl, dest_addr=dest_addr)

    def _send_ack(self, dest_addr):
        ack = ManagerPDU.create_ack()
        self._send_pdu(ack, dest_addr=dest_addr)

    def _send_ping(self, dest_addr=net.layers.base.FLOOD_ADDRESS):
        ping = ManagerPDU.create_ping()
        self._send_pdu(ping, dest_addr=dest_addr)

    def _send_pdu(self, data_unit, dest_addr=None):
        self._log_send_pdu(data_unit)
        self._send(data_unit.to_string(), dest_addr=dest_addr)

    def log(self, message):
        # TODO: Fix this.
        prefix = "(%2s, %s, D=%s/%s, R=%s/%s, k = %s, t_min = %s, t_max = %s, delay = %s)" % \
            (self.addr, Protocol.get_name(self.PROTOCOL),
                self.D_PAGE_SIZE, self.D_PACKET_SIZE,
                self.R_PAGE_SIZE, self.R_PACKET_SIZE,
                self.K, self.T_MIN, self.T_MAX, self.DELAY)
        self.logger.info("%s - %s" % (prefix, message))

    def _log_receive_pdu(self, data_unit, sender_addr):
        self.log("Received message from %3s: %s" % (sender_addr, repr(data_unit)))

    def _log_send_pdu(self, data_unit):
        self.log("Sending message (%s): %s" % (len(data_unit.to_string()), repr(data_unit)))


def main(args):
    manager = Manager.create_and_run_application()
    manager.set_mode(args.mode)
    manager.set_nodes(args.nodes)
    control_pdu = ManagerPDU.create_ctrl(
        protocol=Protocol.get_protocol(args.protocol),
        d_page_size=args.dpagesize,
        d_packet_size=args.dpacketsize,
        r_page_size=args.rpagesize,
        r_packet_size=args.rpacketsize,
        k=args.k,
        t_min=args.tmin,
        t_max=args.tmax,
        delay=args.delay,
        frame_delay=args.framedelay,
        t_r=args.t_r,
        t_tx=args.t_tx,
        w=args.w,
        rx_max=args.rx_max)
    manager._update_ctrl_parameters(control_pdu)

    # Start.
    seed_data = args.file.read()
    args.file.close()
    if manager.mode == Mode.NORMAL:
        manager.start_normal(seed_data, args.version)
    while True:
        if manager.mode == Mode.PING:
            manager.send_ping()
            time.sleep(2)
        elif manager.mode == Mode.CONTROL:
            manager.send_ctrl()
            time.sleep(2)
        else:
            time.sleep(100)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manager Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL,
                        choices=[Mode.NORMAL, Mode.CONTROL, Mode.LISTEN, Mode.PING])

    seed = parser.add_argument_group('Protocol Seed Data')
    seed.add_argument('--file', '-f', type=argparse.FileType(), required=True,
                      help='File to seed as the initial version of the data.')
    seed.add_argument('--version', '-v', type=int, default=1)

    config = parser.add_argument_group('Protocol Configuration')
    config.add_argument('--protocol', '-p', choices=Protocol.NAMES,
                        type=str, default=Protocol.NAMES[0],
                        help='The protocol to run.')
    config.add_argument('-k', type=int, default=1,
                        help='Number of overheard messages to trigger message suppression.')
    config.add_argument('--tmin', type=float, default=1,
                        help='The lower bound for the round window length, in seconds.')
    config.add_argument('--tmax', type=float, default=60 * 10,
                        help='The upper bound for the round window length, in seconds.')
    config.add_argument('--delay', type=int, default=3,
                        help='The number of seconds to wait before starting the protocol.')
    config.add_argument('--framedelay', type=float, default=.02,
                        help='The time taken for a frame to leave the xbee after it is sent.')
    config.add_argument('--t_r', type=float, default=.5)
    config.add_argument('--t_tx', type=float, default=.2)
    config.add_argument('--w', type=int, default=10)
    config.add_argument('--rx_max', type=int, default=2)

    # Deluge page/packet size
    deluge = parser.add_argument_group('Deluge Specific Configuration')
    deluge.add_argument('--dpagesize', type=int, default=1020,
                        help='Deluge: The number of bytes in each page.')
    deluge.add_argument('--dpacketsize', type=int, default=60,
                        help='Deluge: The number of bytes in each packet.')

    # Rateless page/packet size
    rateless = parser.add_argument_group('Rateless Specific Configuration')
    rateless.add_argument('--rpagesize', type=int, default=900,
                          help='Rateless: The number of bytes in each page.')
    rateless.add_argument('--rpacketsize', type=int, default=45,
                          help='Rateless: The number of bytes in each packet.')

    network = parser.add_argument_group('Network Configuration')
    network.add_argument('-n', '--nodes', type=int, metavar='NODES', nargs='+',
                         help='The node ids of the nodes in the network.')

    args = parser.parse_args()
    main(args)
