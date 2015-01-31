import net.layers.datalink
import net.layers.physical
import Queue as queue
import sim.layers.transport
import sim.radio
import threading

class Node(threading.Thread):
    def __init__(self, addr, radio):
        super(Node, self).__init__()
        self.daemon = True
        self.addr = addr
        self.radio = radio

        # Messages from other node waiting to be received by our radio.
        self.incoming_buffer = queue.Queue()

        # Messages from this node's radio waiting to be sent out.
        self.outgoing_buffer = queue.Queue()

        # Simulated socket buffer for transport layer
        self.transport_layer_socket_queue = queue.Queue()

        # Map of app.ADDRESS to applications
        self.applications = {}

        self._init_create_layers()

    def _init_create_layers(self):
        self.physical = net.layers.physical.Physical(self.addr, self.radio)
        self.datalink = net.layers.datalink.DataLink(self.addr)

        # Simulated transport layer.
        self.transport = sim.layers.transport.Transport(self.addr)

        # Start up Physical layer.
        # - listen for incoming packets on the radio
        self.physical.start_listen_to_radio()
        # - handle outgoing packets from DataLink layer
        self.physical.start_handling_outgoing(self.datalink.get_outgoing_queue())

        # Start up DataLink layer.
        # - handle incoming packets from Physical layer
        self.datalink.start_handling_incoming(self.physical.get_incoming_queue())
        # - handle outgoing packets from Transport layer
        self.datalink.start_handling_outgoing(self.transport.get_outgoing_queue())

        # Start up Transport layer.
        # - handle incoming packets from DataLink layer
        self.transport.start_handling_incoming(self.datalink.get_incoming_queue())
        # - handle outgoing packets from various Applications
        self.transport.start_handling_outgoing(self.transport_layer_socket_queue)

    def start_application(self, app):
        assert app.ADDRESS not in self.applications
        self.applications[app.ADDRESS] = app
        app.set_outgoing_queue(self.transport_layer_socket_queue)
        app.start_handling_incoming(
            self.transport.get_incoming_queue_for_app(app.ADDRESS))

    def get_application(self, socket_address):
        return self.applications[socket_address]

    def _process_incoming(self):
        while True:
            incoming = self.incoming_buffer.get()
            self.radio.put_incoming(incoming)

    def _process_outgoing(self):
        while True:
            outgoing = self.radio.get_outgoing()
            self.outgoing_buffer.put(outgoing)

    def run(self):
        t1 = threading.Thread(target=self._process_incoming)
        t2 = threading.Thread(target=self._process_outgoing)
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()

    @classmethod
    def create(cls, addr):
        radio = sim.radio.Radio(addr)
        return Node(addr, radio)
