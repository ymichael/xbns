from net.layers.transport import TransportPDU

import net.layers.transport
import Queue as queue


class Transport(net.layers.transport.Transport):
    """Simulated Transport layer."""
    def __init__(self, addr):
        super(Transport, self).__init__(addr)

        # Map of app.ADDRESS to each application's simulated socket buffer.
        self._incoming_queues_for_apps = {}

    def get_incoming_queue_for_app(self, socket_address):
        if socket_address not in self._incoming_queues_for_apps:
            self._incoming_queues_for_apps[socket_address] = queue.Queue()
        return self._incoming_queues_for_apps[socket_address]

    def _handle_incoming(self, data):
        transport_pdu = TransportPDU.from_string(data)
        app_socket_address = ("", transport_pdu.dest_port)
        incoming_queue = self.get_incoming_queue_for_app(app_socket_address)
        incoming_queue.put(data)
