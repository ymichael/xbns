import base


class Application(base.BaseLayer):
    def process_incoming(self, data, metadata=None):
    	self.logger.debug("(%s): Received: %s" % (self.addr, data))
        # print data

    def send(self, data, dest_addr=None):
        metadata = base.MetaData()
        if dest_addr is not None:
            metadata.dest_addr = dest_addr

        self.process_outgoing(data, metadata)
        self.logger.debug("(%s): Sent: %s" % (self.addr, data))
