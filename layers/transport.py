import base


class Transport(base.BaseLayer):
    def __init__(self):
        super(Transport, self).__init__()

    def process_incoming(self, data):
        self.incoming_queue.put(data)

    def process_outgoing(self, data):
        self.outgoing_queue.put(data)
