import base


class Application(base.BaseLayer):
    def get_port(self):
        """Returns port number associated with the application layer.

        Subclass should override this.
        """
        return None

    def process_incoming(self, data, metadata=None):
        self.logger.debug("(%s, %s): Received: %s" % \
            (self.addr, self.get_port(), data))

    def send(self, data, dest_addr=None):
        metadata = base.MetaData()
        metadata.port = self.get_port()
        assert metadata.port is not None
        if dest_addr is not None:
            metadata.dest_addr = dest_addr

        self.process_outgoing(data, metadata)
        self.logger.debug("(%s, %s): Sent: %s" % \
            (self.addr, self.get_port(), data))

    def start_incoming(self, incoming_layer):
        while True:
            data, metadata = incoming_layer.get_incoming(self.get_port())
            self.process_incoming(data, metadata)