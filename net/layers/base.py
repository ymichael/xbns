import Queue as queue
import logging
import threading

 
class MetaData(object):
    # 65535 => \xff\xff
    BROADCAST_ADDR = 65535

    # Default dest_addr is a broadcast.
    DEST_ADDR = BROADCAST_ADDR

    def __init__(self):
        self.dest_addr = self.DEST_ADDR
        self.source_addr = None
        self.sender_addr = None


class BaseLayer(object):
    """Base class for each layer."""

    def __init__(self):
        # Each layer has a logger that logs to the console.
        self.logger = logging.getLogger(self.__class__.__name__)
        # TODO: Refactor debug level as a cli argument.
        self.logger.setLevel(logging.DEBUG)
        if len(self.logger.handlers) == 0:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(name)-10s - %(levelname)-8s: %(message)s"))
            self.logger.addHandler(handler)
        self.addr = None
        # From this layer to a higher layer.
        self._incoming_queue = queue.Queue()
        # From this layer to a lower layer.
        self._outgoing_queue = queue.Queue()

    def set_addr(self, addr):
        self.addr = addr

    def is_incoming_empty(self):
        """Returns whether the incoming queue is empty.

        Whether there is any incoming data buffered for the next (higher) layer.
        """
        return self._incoming_queue.empty()

    def is_outgoing_empty(self):
        """Returns whether the outgoing queue is empty.

        Whether there is any outgoing data buffered for the next (lower) layer.
        """
        return self._outgoing_queue.empty()

    def get_incoming(self):
        """Returns the next item in the incoming queue.

        Blocks if queue is empty.
        """
        return self._incoming_queue.get()

    def get_outgoing(self):
        """Returns the next item in the outgoing queue.

        Blocks if queue is empty.
        """
        return self._outgoing_queue.get()

    def put_incoming(self, data, metadata=None):
        self._incoming_queue.put((data, metadata))

    def put_outgoing(self, data, metadata=None):
        self._outgoing_queue.put((data, metadata))

    def process_incoming(self, data, metadata=None):
        """Process an incoming unit of data from a lower layer.

        Subclasses should override this method.
        """
        self.put_incoming(data, metadata)

    def process_outgoing(self, data, metadata=None):
        """Process an outgoing unit of data from a upper layer.

        Subclasses should override this method.
        """
        self.put_outgoing(data, metadata)

    def start_incoming(self, incoming_layer):
        while True:
            data, metadata = incoming_layer.get_incoming()
            self.process_incoming(data, metadata)

    def start_outgoing(self, outgoing_layer):
        while True:
            data, metadata = outgoing_layer.get_outgoing()
            self.process_outgoing(data, metadata)

    def start(self, incoming_layer=None, outgoing_layer=None):
        """Starts threads for either layer, if given."""
        if incoming_layer is not None:
            incoming = threading.Thread(
                    target=self.start_incoming, args=(incoming_layer,))
            incoming.setDaemon(True)
            incoming.start()

        if outgoing_layer is not None:
            outgoing = threading.Thread(
                    target=self.start_outgoing, args=(outgoing_layer,))
            outgoing.setDaemon(True)
            outgoing.start()