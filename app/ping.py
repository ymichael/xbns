import net.layers.application
import net.layers.transport
import pong
import time


class Ping(net.layers.application.Application):
    """Sends pings."""
    ADDRESS = ("", 11005)

    def _handle_incoming(self, data):
        pdu = net.layers.transport.TransportPDU.from_string(data)
        self.log("Received a %s from %s" % (pdu.message, pdu.source_addr))

    def broadcast_ping(self):
        dest_port = pong.Pong.ADDRESS[1]
        self._send('PING', dest_port)
        self.log("BROADCAST a PING")


def main():
    app = Ping.create_and_run_application()
    while True:
        app.broadcast_ping()
        time.sleep(1)


if __name__ == '__main__':
    main()
