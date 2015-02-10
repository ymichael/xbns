import argparse
import deluge
import net.layers.application
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


class ManagerPDU(object):
    ACK = 0
    CTRL = 1

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
        self.page_size = x[1]
        self.packet_size = x[2]
        self.k = x[3]
        self.t_min = x[4]
        self.t_max = x[5]
        self.delay = x[6]

    def is_ctrl(self):
        return self.msg_type == self.CTRL

    def is_ack(self):
        return self.msg_type == self.ACK

    @property
    def type(self):
        if self.is_ctrl():
            return 'CTRL'
        elif self.is_ack():
            return 'ACK'

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
        elif self.is_ack():
            return self.type

    def _repr_ctrl(self):
        return "%4s, %s, %s/%s, k = %s, t_min = %s, t_max = %s, delay = %s" % \
            (self.type, Protocol.get_name(self.protocol), self.page_size,
                    self.packet_size, self.k, self.t_min, self.t_max, self.delay)

    @classmethod
    def create_ctrl_packet(cls,
            protocol=Protocol.DELUGE,
            page_size=1024, packet_size=64,
            k=1, t_min=1, t_max=60 * 10, delay=5):
        assert page_size % packet_size == 0
        assert t_min <= t_max
        assert protocol < len(Protocol.NAMES)
        message = pickle.dumps(
            [protocol, page_size, packet_size, k, t_min, t_max, delay])
        return cls(cls.CTRL, message)

    @classmethod
    def create_ack_packet(cls):
        return cls(cls.ACK, message="")


class Manager(net.layers.application.Application):
    """Run and manage both rateless and deluge concurrently."""
    ADDRESS = ("", 11006)

    # Parameters
    PROTOCOL = Protocol.DELUGE
    PAGE_SIZE = 1024
    PACKET_SIZE = 64
    PACKETS_PER_PAGE = PAGE_SIZE / PACKET_SIZE
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

    def _process_ctrl(self, data_unit):
        self._send_ack()
        self._update_ctrl_parameters(data_unit)
        if self.mode == Mode.NORMAL_MODE:
            active = self.apps[self.PROTOCOL]
            active._start_next_round(self.DELAY)

    def _update_ctrl_parameters(self, data_unit):
        self.PROTOCOL = data_unit.protocol
        self.PAGE_SIZE = data_unit.page_size
        self.PACKET_SIZE = data_unit.packet_size
        self.PACKETS_PER_PAGE = self.PAGE_SIZE / self.PACKET_SIZE
        self.K = data_unit.k
        self.T_MIN = data_unit.t_min
        self.T_MAX = data_unit.t_max
        self.DELAY = data_unit.delay

        # TMP.
        rateless_deluge.ROWS_REQUIRED = self.PACKETS_PER_PAGE
        
        # Update the two protocols.
        self._update_protocol(self.deluge)
        self._update_protocol(self.rateless)

    def _update_protocol(self, protocol):
        protocol.stop()
        data = protocol.get_data()
        protocol.PAGE_SIZE = self.PAGE_SIZE
        protocol.PACKET_SIZE = self.PACKET_SIZE
        protocol.PACKETS_PER_PAGE = self.PACKETS_PER_PAGE
        protocol.new_version(1, data, force=True, start=False)
        protocol.T_MIN = self.T_MIN
        protocol.T_MAX = self.T_MAX
        protocol.K = self.K
        protocol._reset_round_state()

    def start(self, version, data):
        if self.mode == Mode.NORMAL_MODE:
            active = self.apps[self.PROTOCOL]
            active.new_version(version, data, force=True, start=False)
            active._start_next_round(self.DELAY)
        elif self.mode == Mode.CONTROL_MODE:
            self._send_ctrl()

    def _send_ctrl(self):
        ctrl = ManagerPDU.create_ctrl_packet(
            protocol=self.PROTOCOL,
            page_size=self.PAGE_SIZE,
            packet_size=self.PACKET_SIZE,
            k=self.K,
            t_min=self.T_MIN,
            t_max=self.T_MAX,
            delay=self.DELAY)
        self._send_pdu(ctrl)

    def _send_ack(self):
        self._send_pdu(ManagerPDU.create_ack_packet())

    def _send_pdu(self, data_unit):
        self._log_send_pdu(data_unit)
        self.send(data_unit.to_string())

    def log(self, message):
        prefix = "(%2s, %s, %s/%s, k = %s, t_min = %s, t_max = %s, delay = %s)" % \
            (self.addr, Protocol.get_name(self.PROTOCOL), self.PAGE_SIZE,
                    self.PACKET_SIZE, self.K, self.T_MIN, self.T_MAX, self.DELAY)
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
        page_size=args.pagesize,
        packet_size=args.packetsize,
        k=args.k,
        t_min=args.tmin,
        t_max=args.tmax,
        delay=args.delay)
    manager._update_ctrl_parameters(control_pdu)

    # Start.
    seed_data = args.file.read()
    args.file.close()
    manager.start(args.version, seed_data)

    while True:
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manager Application')
    parser.add_argument('--mode', '-m', type=str, default=Mode.NORMAL_MODE,
                        choices=[Mode.NORMAL_MODE, Mode.CONTROL_MODE])

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
    config.add_argument('--tmin', type=int, default=1,
                        help='The lower bound for the round window length, in seconds.')
    config.add_argument('--tmax', type=int, default=60 * 10,
                        help='The upper bound for the round window length, in seconds.')
    config.add_argument('--pagesize', type=int, default=1024,
                        help='The number of bytes in each page.')
    config.add_argument('--packetsize', type=int, default=64,
                        help='The number of bytes in each packet.')
    config.add_argument('--delay', type=int, default=3,
                        help='The number of seconds to wait before starting the protocol.')
    args = parser.parse_args()
    main(args)
