import argparse
import deluge
import net.layers.application
import net.layers.base
import net.layers.transport
import pickle
import rateless_deluge
import struct
import time


class Protocol(object):
    DELUGE = 0
    RATELESS = 1

    NAMES = [
        "deluge",
        "rateless",
    ]

    @classmethod
    def get_protocol(cls, string):
        return cls.NAMES.index(string)

    @classmethod
    def get_name(cls, protocol):
        return cls.NAMES[protocol]


class Mode(object):
    # Run the protocols normally with the given parameters.
    NORMAL_MODE = "NORMAL"
    # Update already running protocols to the given parameters (OTA).
    CONTROL_MODE = "CONTROL"
    # Listen mode, don't interupt current protocol.
    LISTEN_MODE = "LISTEN"


class ManagerPDU(object):
    ACK = 0
    CTRL = 1
    PING = 2

    HEADER_PREFIX = "B"
    HEADER_PREFIX_SIZE = struct.calcsize(HEADER_PREFIX)

    def __init__(self, msg_type, message):
        self.msg_type = msg_type
        self.message = message

        if self.is_ctrl():
            self.__init_ctrl()

    def __init_ctrl(self):
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

    def is_ctrl(self):
        return self.msg_type == self.CTRL

    def is_ping(self):
        return self.msg_type == self.PING

    def is_ack(self):
        return self.msg_type == self.ACK

    @property
    def type(self):
        if self.is_ctrl():
            return 'CTRL'
        elif self.is_ack():
            return 'ACK'
        elif self.is_ping():
            return 'PING'

    def to_string(self):
        header = struct.pack(self.HEADER_PREFIX, self.msg_type)
        return header + self.message

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_PREFIX, data[:cls.HEADER_PREFIX_SIZE])
        return cls(x[0], data[cls.HEADER_PREFIX_SIZE:])

    def __repr__(self):
        if self.is_ctrl():
            return self._repr_ctrl()
        return self.type

    def _repr_ctrl(self):
        return "%4s, %s, d = %s/%s, r = %s/%s k = %s, t_min = %s, t_max = %s, delay = %s, frame_delay = %s" % \
            (self.type, Protocol.get_name(self.protocol),
                self.d_page_size, self.d_packet_size,
                self.r_page_size, self.r_packet_size,
                self.k, self.t_min, self.t_max, self.delay, self.frame_delay)

    @classmethod
    def create_ctrl_packet(cls,
            protocol=Protocol.DELUGE,
            d_page_size=1020, d_packet_size=60,
            r_page_size=900, r_packet_size=45,
            k=1, t_min=1, t_max=60 * 10, delay=5,
            frame_delay=.02):
        assert d_page_size % d_packet_size == 0
        assert r_page_size % r_packet_size == 0
        assert t_min <= t_max
        assert protocol < len(Protocol.NAMES)
        message = pickle.dumps(
            [protocol,
                d_page_size, d_packet_size,
                r_page_size, r_packet_size,
                k, t_min, t_max, delay, frame_delay])
        return cls(cls.CTRL, message)

    @classmethod
    def create_ack_packet(cls):
        return cls(cls.ACK, message="")

    @classmethod
    def create_ping_packet(cls):
        return cls(cls.PING, message="")


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

    def __init__(self, addr):
        super(Manager, self).__init__(addr)
        self.apps = {}
        self._create_protocol_applications()
        self.deluge.stop()
        self.rateless.stop()

    def _create_protocol_applications(self):
        self.apps[Protocol.DELUGE] = deluge.Deluge.create_and_run_application()
        self.apps[Protocol.RATELESS] = \
            rateless_deluge.RatelessDeluge.create_and_run_application()

    def set_mode(self, mode):
        self.mode = mode

    @property
    def deluge(self):
        return self.apps.get(Protocol.DELUGE)

    @property
    def rateless(self):
        return self.apps.get(Protocol.RATELESS)

    def _handle_incoming(self, data):
        transport_pdu = net.layers.transport.TransportPDU.from_string(data)
        data_unit = ManagerPDU.from_string(transport_pdu.message)
        self._log_receive_pdu(data_unit, transport_pdu.source_addr)
        if data_unit.is_ctrl():
            self._process_ctrl(data_unit)

        if data_unit.is_ping():
            self._process_ping()

    def _process_ping(self):
        self._send_ack()
        # Get active protocol to send ADV is in normal mode.
        if self.mode == Mode.NORMAL_MODE:
            active = self.apps[self.PROTOCOL]
            active._send_adv(force=True)

    def _process_ctrl(self, data_unit):
        self._send_ack()
        self._update_ctrl_parameters(data_unit)
        if self.mode == Mode.NORMAL_MODE:
            active = self.apps[self.PROTOCOL]
            active._start_next_round(self.DELAY)

    def _update_ctrl_parameters(self, data_unit):
        self.PROTOCOL = data_unit.protocol

        self.D_PAGE_SIZE = data_unit.d_page_size
        self.D_PACKET_SIZE = data_unit.d_packet_size
        self.D_PACKETS_PER_PAGE = self.D_PAGE_SIZE / self.D_PACKET_SIZE

        self.R_PAGE_SIZE = data_unit.r_page_size
        self.R_PACKET_SIZE = data_unit.r_packet_size
        self.R_PACKETS_PER_PAGE = self.R_PAGE_SIZE / self.R_PACKET_SIZE

        self.K = data_unit.k
        self.T_MIN = data_unit.t_min
        self.T_MAX = data_unit.t_max
        self.DELAY = data_unit.delay
        self.FRAME_DELAY = data_unit.frame_delay

        # Update the two protocols.
        self._update_deluge()
        self._update_rateless()

    def _update_deluge(self):
        self.deluge.stop()
        data = self.deluge.get_data()
        self.deluge.PAGE_SIZE = self.D_PAGE_SIZE
        self.deluge.PACKET_SIZE = self.D_PACKET_SIZE
        self.deluge.PACKETS_PER_PAGE = self.D_PACKETS_PER_PAGE
        self.deluge.new_version(1, data, force=True, start=False)
        self.deluge.T_MIN = self.T_MIN
        self.deluge.T_MAX = self.T_MAX
        self.deluge.K = self.K
        self.deluge.FRAME_DELAY = self.FRAME_DELAY
        self.deluge._reset_round_state()

    def _update_rateless(self):
        self.rateless.stop()
        data = self.rateless.get_data()
        self.rateless.PAGE_SIZE = self.R_PAGE_SIZE
        self.rateless.PACKET_SIZE = self.R_PACKET_SIZE
        self.rateless.PACKETS_PER_PAGE = self.R_PACKETS_PER_PAGE
        self.rateless.new_version(1, data, force=True, start=False)
        self.rateless.T_MIN = self.T_MIN
        self.rateless.T_MAX = self.T_MAX
        self.rateless.K = self.K
        self.rateless.FRAME_DELAY = self.FRAME_DELAY
        self.rateless._reset_round_state()

        rateless_deluge.ROWS_REQUIRED = self.R_PACKETS_PER_PAGE
        self.rateless.PDU_CLS.DATA_FORMAT = "II" + ("B" * self.R_PACKETS_PER_PAGE) + \
            ("B" * self.R_PACKET_SIZE)

    def start_normal(self, version, data):
        active = self.apps[self.PROTOCOL]
        active.new_version(version, data, force=True, start=False)
        active._start_next_round(self.DELAY)

    def _send_ctrl(self):
        ctrl = ManagerPDU.create_ctrl_packet(
            protocol=self.PROTOCOL,
            d_page_size=self.D_PAGE_SIZE,
            d_packet_size=self.D_PACKET_SIZE,
            r_page_size=self.R_PAGE_SIZE,
            r_packet_size=self.R_PACKET_SIZE,
            k=self.K,
            t_min=self.T_MIN,
            t_max=self.T_MAX,
            delay=self.DELAY)
        self._send_pdu(ctrl, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def _send_ack(self):
        ack = ManagerPDU.create_ack_packet()
        self._send_pdu(ack, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def _send_ping(self):
        ping = ManagerPDU.create_ping_packet()
        self._send_pdu(ping, dest_addr=net.layers.base.FLOOD_ADDRESS)

    def _send_pdu(self, data_unit, dest_addr=None):
        self._log_send_pdu(data_unit)
        self._send(data_unit.to_string(), dest_addr=dest_addr)

    def log(self, message):
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
    control_pdu = ManagerPDU.create_ctrl_packet(
        protocol=Protocol.get_protocol(args.protocol),
        d_page_size=args.dpagesize,
        d_packet_size=args.dpacketsize,
        r_page_size=args.rpagesize,
        r_packet_size=args.rpacketsize,
        k=args.k,
        t_min=args.tmin,
        t_max=args.tmax,
        delay=args.delay,
        frame_delay=args.framedelay)
    manager._update_ctrl_parameters(control_pdu)

    # Start.
    seed_data = args.file.read()
    args.file.close()
    if manager.mode == Mode.NORMAL_MODE:
        manager.start_normal(args.version, seed_data)
    if manager.mode == Mode.LISTEN_MODE:
        manager._send_ping()
    while True:
        if manager.mode == Mode.CONTROL_MODE:
            manager._send_ctrl()
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manager Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL_MODE,
                        choices=[Mode.NORMAL_MODE, Mode.CONTROL_MODE,
                            Mode.LISTEN_MODE])

    seed = parser.add_argument_group('Protocol Seed Data')
    seed.add_argument('--file', '-f', type=argparse.FileType(), required=True,
                      help='File to seed as the initial version of the data.')
    seed.add_argument('--version', '-v', type=int, default=1,
                      help='The version number of the seed file.')

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

    # Deluge page/packet size
    config.add_argument('--dpagesize', type=int, default=1020,
                        help='Deluge: The number of bytes in each page.')
    config.add_argument('--dpacketsize', type=int, default=60,
                        help='Deluge: The number of bytes in each packet.')

    # Rateless page/packet size
    config.add_argument('--rpagesize', type=int, default=900,
                        help='Rateless: The number of bytes in each page.')
    config.add_argument('--rpacketsize', type=int, default=45,
                        help='Rateless: The number of bytes in each packet.')

    config.add_argument('--delay', type=int, default=3,
                        help='The number of seconds to wait before starting the protocol.')
    config.add_argument('--framedelay', type=float, default=.02,
                        help='The time taken for a frame to leave the xbee after it is sent.')
    args = parser.parse_args()
    main(args)
