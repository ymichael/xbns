import Queue as queue
import base
import struct
import threading


class TransportPDU(object):
    # application id/port number: I
    HEADER_FORMAT = "I"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, port, message):
        self.port = port
        self.message = message

    def to_string(self):
        header = struct.pack(self.HEADER_FORMAT, self.port)
        return header + self.message

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        return TransportPDU(x[0], data[cls.HEADER_SIZE:])


class Transport(base.BaseLayer):
    """Transport Layer.

    - Responsible for multiplexing between application layers.
    - Allows multiple application to run on the same node.
    """
    def __init__(self):
        super(Transport, self).__init__()
        # Map of ports to apps
        self.apps = {}
        self.apps_incoming_queues = {}

    def get_incoming(self, port):
        return self.apps_incoming_queues[port].get()

    def put_incoming(self, data, metadata=None):
        # Forward to correct application layer.
        assert metadata.port is not None
        assert metadata.port in self.apps
        self.apps_incoming_queues[metadata.port].put((data, metadata))

    def process_incoming(self, data, metadata=None):
        data_unit = TransportPDU.from_string(data)
        metadata = metadata or base.MetaData()
        metadata.port = data_unit.port
        self.put_incoming(data_unit.message, metadata)

    def process_outgoing(self, data, metadata=None):
        # Get values from metadata.
        port = metadata.port
        data_unit = TransportPDU(port, data)
        self.put_outgoing(data_unit.to_string(), metadata)

    def add_app(self, app):
        # Port numbers should be unique.
        assert app.get_port() not in self.apps
        self.apps[app.get_port()] = app
        self.apps_incoming_queues[app.get_port()] = queue.Queue()

        # Listen on the application's outgoing queue.
        app_outgoing = threading.Thread(
            target=self.start_outgoing, args=(app,))
        app_outgoing.setDaemon(True)
        app_outgoing.start()
