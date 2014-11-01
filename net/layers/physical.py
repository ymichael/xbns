import base
import threading


class Physical(base.BaseLayer):
    """Physical layer, interfaces with a Radio."""
    def __init__(self, radio):
        super(Physical, self).__init__();
        self.radio = radio

    def process_outgoing(self, data, metadata=None):
        self.radio.broadcast(data)

    def listen_to_radio(self):
        while True:
            data, sender_addr = self.radio.receive()
            metadata = base.MetaData()
            metadata.sender_addr = sender_addr
            self.put_incoming(data, metadata)

    def start(self, incoming_layer=None, outgoing_layer=None):
        super(Physical, self).start(outgoing_layer=outgoing_layer)
        t = threading.Thread(target=self.listen_to_radio)
        t.setDaemon(True)
        t.start()
