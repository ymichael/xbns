import Queue as queue
import threading
import utils.logger

# 65535 => \xff\xff
BROADCAST_ADDRESS = 65535
FLOOD_ADDRESS = 65534


class BaseLayer(object):
    """Base class for each layer."""

    def __init__(self, addr):
        self._init_logger()
        self.addr = addr

    def _init_logger(self):
        # Each layer has a logger that logs to the console.
        self.logger = utils.logger.get_logger(self.__class__.__name__)
        self.logger.info("Starting up.")

    def start_handling_incoming(self, queue):
        self._start_handler(queue, self._handle_incoming)

    def start_handling_outgoing(self, queue):
        self._start_handler(queue, self._handle_outgoing)

    def _start_handler(self, queue, handler):
        t = threading.Thread(target=self._handler, args=(queue, handler))
        t.setDaemon(True)
        t.start()

    def _handler(self, queue, handler):
        while True:
            data = queue.get()
            handler(data)

    def get_outgoing_queue(self):
        # From this layer to a lower layer.
        raise NotImplementedError

    def get_incoming_queue(self):
        # From this layer to a higher layer.
        raise NotImplementedError

    def _handle_incoming(self, data):
        raise NotImplementedError

    def _handle_outgoing(self, data):
        raise NotImplementedError
