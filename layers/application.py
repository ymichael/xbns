import base


class Application(base.BaseLayer):
    def __init__(self):
        super(Application, self).__init__()

    def process_incoming(self, data):
        print data

    def process_outgoing(self, data):
        self.outgoing_queue.put(data)

    def send(self, data):
        self.process_outgoing(data)
