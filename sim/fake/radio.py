from net.radio.base import BaseRadio
import Queue as queue


class FakeRadio(BaseRadio):
    def __init__(self, addr):
        self.addr = addr
        self.outgoing_queue = queue.Queue()
        self.incoming_queue = queue.Queue()

    def broadcast(self, data):
        self.outgoing_queue.put(data)

    def receive(self):
        return self.incoming_queue.get()

    def put_incoming(self, frame):
        self.incoming_queue.put(frame)

    def get_outgoing(self):
        return self.outgoing_queue.get()