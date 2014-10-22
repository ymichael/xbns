import Queue as queue


class BaseLayer(object):
    """Base class for each layer."""
    def __init__(self):
        self.incoming_queue = queue.Queue()
        self.outgoing_queue = queue.Queue()

    def get_incoming(self):
        return self.incoming_queue.get()

    def get_outgoing(self):
        return self.outgoing_queue.get()

    def process_incoming(self, data):
        raise NotImplementedError()

    def process_outgoing(self, data):
        raise NotImplementedError()
