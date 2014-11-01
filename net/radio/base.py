class BaseRadio(object):
    def broadcast(self, data):
        raise NotImplementedError()

    def receive(self):
        """Returns a tuple of (data, sender_addr)."""
        raise NotImplementedError()
