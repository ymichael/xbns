import app.protocol.deluge
import net.layers.application
import net.layers.transport
import sock
import threading
import utils.pdu


class DataDisseminationPDU(utils.pdu.PDU):
    TYPES = [
        'FOR_APP',       # Intended for the application.
        'FOR_PROTOCOL',  # Intended for the protocol.
    ]


class DataDissemination(net.layers.application.Application):
    """Extends `net.layers.application` with additional data dissemination
    methods.

    These additional methods use a subclass of `app.protocol` instead of
    talking directly to the transport layer:
    - disseminate(self, data)
    - handle_incoming_dissemination(self, data)
    """

    PDU_CLS = DataDisseminationPDU

    def __init__(self, addr, protocol=None):
        super(DataDissemination, self).__init__(addr)
        self.protocol = protocol or self.create_protocol()
        self._init_protocol()
        self.start()

    def _handle_incoming(self, data):
        transport_pdu = net.layers.transport.TransportPDU.from_string(data)
        dd_pdu = self.PDU_CLS.from_string(transport_pdu.message)
        if dd_pdu.is_for_app():
            self._handle_incoming_message(
                dd_pdu.message, transport_pdu.source_addr)
        elif dd_pdu.is_for_protocol():
            self.protocol._handle_incoming_message(
                dd_pdu.message, transport_pdu.source_addr)

    def _init_protocol(self):
        self.protocol.addr = self.addr
        # Override protocol's send method.
        app = self
        def send_to_protocol(data):
            app._send_to_protocol(data)
        self.protocol._send = send_to_protocol
        self.protocol.start()

    def start(self):
        t = threading.Thread(target=self._check_protocol_received)
        t.setDaemon(True)
        t.start()

    def _check_protocol_received(self):
        while True:
            data = self.protocol.get_received_blocking()
            self._handle_incoming_dissemination(data)
        
    def _send_to_protocol(self, data):
        dd_pdu = self.PDU_CLS.create_for_protocol(data)
        self._send(dd_pdu.to_string())

    def _send_to_app(self, data):
        dd_pdu = self.PDU_CLS.create_for_app(data)
        self._send(dd_pdu.to_string())

    def disseminate(self, data):
        self.protocol.disseminate(data)

    def _handle_incoming_dissemination(self, data):
        raise NotImplementedError

    @classmethod
    def create_protocol(cls):
        raise NotImplementedError

    @classmethod
    def create_and_run_application(cls):
        import config
        app = cls(config.ADDR, cls.create_protocol())
        app.log("Starting Application...")

        # Start up Application
        # - handle incoming packets from the transport layer.
        app.log("Connecting to incoming socket...")
        app.start_handling_incoming(app.get_incoming_socket_reader())

        # Create BufferedWriter to write to socket.
        app.log("Connecting to outgoing socket...")
        buffered_writer = sock.writer.BufferedWriter(
            net.layers.transport.Transport.ADDRESS)
        buffered_writer.start()
        app.set_outgoing_queue(buffered_writer)

        app.log("Application started!")
        return app