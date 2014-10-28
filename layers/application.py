import base


class Application(base.BaseLayer):
    def process_incoming(self, data, metadata=None):
        print data

    def send(self, data):
        self.process_outgoing(data)
