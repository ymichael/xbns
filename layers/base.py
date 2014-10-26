import Queue as queue


class BaseLayer(object):
    """Base class for each layer."""
    def __init__(self):
        # From this layer to a higher layer.
        self.incoming_queue = queue.Queue()
        # From this layer to a lower layer.
        self.outgoing_queue = queue.Queue()

    def is_incoming_empty(self):
        """Returns whether the incoming queue is empty.

        Whether there is any incoming data buffered for the next (higher) layer.
        """
        return self.incoming_queue.empty()

    def is_outgoing_empty(self):
        """Returns whether the outgoing queue is empty.

        Whether there is any outgoing data buffered for the next (lower) layer.
        """
        return self.outgoing_queue.empty()

    def get_incoming(self):
        """Returns the next item in the incoming queue.

        Blocks if queue is empty.
        """
        return self.incoming_queue.get()

    def get_outgoing(self):
        """Returns the next item in the outgoing queue.

        Blocks if queue is empty.
        """
        return self.outgoing_queue.get()

    def process_incoming(self, data):
        raise NotImplementedError()

    def process_outgoing(self, data):
        raise NotImplementedError()
