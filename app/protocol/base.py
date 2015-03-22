import Queue as queue
import threading
import utils.logger


class Base(object):
    """Base class for a Data Dissemination Protocol."""
    def __init__(self):
        self._incoming = queue.Queue()
        self._outgoing = queue.Queue()
        self._init_logger()

        # Check for outgoing data from apps.
        t = threading.Thread(target=self._check_outgoing)
        t.setDaemon(True)
        t.start()

    def _init_logger(self):
        self.logger = utils.logger.get_logger(self.__class__.__name__)
        self.logger.info("Starting up.")

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def _check_outgoing(self):
        while True:
            data = self._outgoing.get()
            self.process_outgoing(data)

    def process_outgoing(self, data):
        raise NotImplementedError(
            "This should be overriden by subclasses.")

    def disseminate(self, data, version=None):
        self._outgoing.put((data, version))

    def received(self, data):
        self._incoming.put(data)

    def get_received_blocking(self):
        return self._incoming.get()

    def _send(self, data):
        raise NotImplementedError(
            "This should be monkey patched by the app using this protocol.")