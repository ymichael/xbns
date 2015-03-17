import config
import logging
import logging.handlers
import Queue as queue
import sys
import threading


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
        # Each layer has a logger that logs to the console.
        self.logger = logging.getLogger(self.__class__.__name__)
        # TODO: Refactor debug level as a cli argument.
        self.logger.setLevel(logging.DEBUG)
        if len(self.logger.handlers) == 0:
            formatter = logging.Formatter("%(name)s - %(levelname)s - %(asctime)s: %(message)s")
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)
            if config.SHOULD_LOG:
                file_handler = logging.handlers.RotatingFileHandler(
                    config.LOG_FILE_NAME, backupCount=20, maxBytes=5242880)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
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

    def disseminate(self, data):
        self._outgoing.put(data)

    def received(self, data):
        self._incoming.put(data)

    def get_received_blocking(self):
        return self._incoming.get()

    def _send(self, data):
        raise NotImplementedError(
            "This should be monkey patched by the app using this protocol.")