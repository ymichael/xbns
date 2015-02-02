import net.layers.application
import net.layers.transport
import ping
import time


class Pong(net.layers.application.Application):
    """Waits for pings and responds."""
    ADDRESS = ("", 11004)

    def _handle_incoming(self, data):
        pdu = net.layers.transport.TransportPDU.from_string(data)
        self.log("Received a %s from %s" % (pdu.message, pdu.source_addr))

        # Respond with a Pong.
        dest_addr = pdu.source_addr
        dest_port = ping.Ping.ADDRESS[1]
        self._send('PONG', dest_port, dest_addr)
        self.log("Sent a PONG to %s" % dest_addr)


def main():
    app = Pong.create_and_run_application()
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
