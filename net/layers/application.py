import base


class Application(base.BaseLayer):
    def process_incoming(self, data, metadata=None):
        print data

    def send(self, data, dest_addr=None):
        metadata = base.MetaData()
        if dest_addr is not None:
            metadata.dest_addr = dest_addr

        self.process_outgoing(data, dest_addr)
