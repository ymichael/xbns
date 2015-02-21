import base
import Queue as queue
import threading


class Physical(base.BaseLayer):
    """Physical layer, interfaces with a Radio."""
    def __init__(self, addr, radio):
        super(Physical, self).__init__(addr);
        self.radio = radio
        self._incoming_queue = queue.Queue()

    def start_listen_to_radio(self):
        listen_to_radio = threading.Thread(target=self._listen_to_radio)
        listen_to_radio.setDaemon(True)
        listen_to_radio.start()

    def _listen_to_radio(self):
        while True:
            data = self.radio.receive()
            if data[0] == self.radio.TYPE_RX:
                self._incoming_queue.put(data[1:])
            elif data[0] == self.radio.TYPE_OTHERS:
                self.logger.info(data)

    def get_incoming_queue(self):
        return self._incoming_queue

    def _handle_outgoing(self, data):
        self.radio.broadcast(data)