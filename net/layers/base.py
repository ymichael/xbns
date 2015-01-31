import Queue as queue
import logging
import threading

# 65535 => \xff\xff
BROADCAST_ADDRESS = 65535


class BaseLayer(object):
    """Base class for each layer."""

    def __init__(self, addr):
        self._init_logger()
        self.addr = addr

    def _init_logger(self):
        # Each layer has a logger that logs to the console.
        self.logger = logging.getLogger(self.__class__.__name__)
        # TODO: Refactor debug level as a cli argument.
        self.logger.setLevel(logging.DEBUG)
        if len(self.logger.handlers) == 0:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(name)-10s - %(levelname)-8s: %(message)s"))
            self.logger.addHandler(handler)

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
