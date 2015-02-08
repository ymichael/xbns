import base
import Queue as queue
import sock.reader
import sock.writer
import socket
import struct
import threading


class TransportPDU(object):
    # H: unsigned short, 2 bytes.
    # source port: H
    # source addr: H
    # dest port: H
    # dest addr: H
    HEADER_FORMAT = "HHHH"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, message, source_port, source_addr, dest_port, dest_addr):
        self.message = message
        self.source_port = source_port
        self.source_addr = source_addr
        self.dest_port = dest_port
        self.dest_addr = dest_addr

    def to_string(self):
        info = (self.source_port, self.source_addr, self.dest_port, self.dest_addr)
        header = struct.pack(self.HEADER_FORMAT, *info)
        return header + self.message

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        return TransportPDU(data[cls.HEADER_SIZE:], *x)


class Transport(base.BaseLayer):
    """Transport Layer.

    - Responsible for multiplexing between application layers.
    - Allows multiple application to run on the same node.
    """
    ADDRESS = ("", 10000)

    def __init__(self, addr):
        super(Transport, self).__init__(addr)

        self._incoming_queue = queue.Queue()

        self._outgoing_queue = queue.Queue()

    def get_incoming_queue(self):
        return self._incoming_queue

    def get_outgoing_queue(self):
        return self._outgoing_queue

    def get_outgoing_socket_reader(self):
        # Lazily create socket reader.
        if not hasattr(self, '_socket_reader'):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind(self.ADDRESS)
            except socket.error as msg:
                self.logger.error(msg)
                raise RuntimeError(msg)
            self._socket_reader = sock.reader.Reader(self.socket)
            self._socket_reader.start()
        return self._socket_reader

    def _handle_incoming(self, data):
        try:
            transport_pdu = TransportPDU.from_string(data)
            app_socket_address = ("", transport_pdu.dest_port)
            with sock.writer.Writer(app_socket_address) as w:
                w.write(data)
        except socket.error as msg:
            self.logger.error(msg)

    def _handle_outgoing(self, data):
        transport_pdu = TransportPDU.from_string(data)
        # DataLink layer expects tuple of (data, dest_addr).
        self._outgoing_queue.put((data, transport_pdu.dest_addr))
