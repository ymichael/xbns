class BaseRadio(object):
    TYPE_RX = 'rx'
    TYPE_OTHERS = 'others'

    def broadcast(self, data):
        raise NotImplementedError()

    def receive(self):
        """Returns a tuple of (type, data, sender_addr)."""
        raise NotImplementedError()
