import net.layers.application
import net.layers.transport
import ping


class Pong(net.layers.application.Application):
    """Waits for pings and responds."""
    ADDRESS = ("", 11004)

    def _handle_incoming(self, data):
        pdu = net.layers.transport.TransportPDU.from_string(data)
        self.logger.debug("Received a %s from %s" % (pdu.message, pdu.source_addr))

        # Respond with a Pong.
        dest_addr = pdu.source_addr
        dest_port = ping.ADDRESS[1]
        self._send('PONG', dest_port, dest_addr)
        self.logger.debug("Sent a PONG to %s" % dest_addr)


def main():
    Pong.run_application()


if __name__ == '__main__':
    main()
