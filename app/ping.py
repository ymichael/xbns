import net.layers.application
import net.layers.transport
import pong
import time


class Ping(net.layers.application.Application):
    """Sends pings."""
    ADDRESS = ("", 11005)

    def _handle_incoming(self, data):
        pdu = net.layers.transport.TransportPDU.from_string(data)
        self.logger.debug("Received a %s from %s" % (pdu.message, pdu.source_addr))

    def _broadcast_ping(self):
        dest_port = pong.Pong.ADDRESS[1]
        self._send('PING', dest_port)
        self.logger.debug("BROADCAST a PING")

    def _idle(self):
        while True:
            self._broadcast_ping()
            time.sleep(1)


def main():
    Ping.run_application()


if __name__ == '__main__':
    main()
