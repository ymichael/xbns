import base
import Queue as queue
import sock.reader
import sock.writer
import socket
import time
import transport


class Application(base.BaseLayer):
    ADDRESS = ('', 11000)

    def __init__(self, addr):
        super(Application, self).__init__(addr)

        self._outgoing_queue = None

    def send(self, data):
        self._send(data)

    def set_outgoing_queue(self, queue):
        self._outgoing_queue = queue

    def _send(self, data, dest_port=None, dest_addr=None):
        source_port = self.ADDRESS[1]
        source_addr = self.addr
        # Default to source port is not specified.
        dest_port = dest_port or source_port
        # Defalut to broadcast if not specified.
        dest_addr = dest_addr or base.BROADCAST_ADDRESS
        transport_pdu = transport.TransportPDU(
            data, source_port, source_addr, dest_port, dest_addr)
        self._outgoing_queue.put(transport_pdu.to_string())

    def get_incoming_socket_reader(self):
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
        transport_pdu = transport.TransportPDU.from_string(data)
        self._handle_incoming_message(transport_pdu.message)

    def _handle_incoming_message(self, message):
        self.log(message)

    def log(self, message):
        prefix = "(%s)" % self.addr
        self.logger.info("%s - %s" % (prefix, message))

    @classmethod
    def create_and_run_application(cls):
        import config
        app = cls(config.ADDR)
        app.log("Starting Application...")

        # Start up Application
        # - handle incoming packets from the transport layer.
        app.log("Connecting to incoming socket...")
        app.start_handling_incoming(app.get_incoming_socket_reader())

        # Create BufferedWriter to write to socket.
        app.log("Connecting to outgoing socket...")
        buffered_writer = sock.writer.BufferedWriter(transport.Transport.ADDRESS)
        buffered_writer.start()
        app.set_outgoing_queue(buffered_writer)

        app.log("Application started!")
        return app


def main():
    Application.create_and_run_application()
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()

