from radio import Radio
import Queue as queue
import net.stack
import threading


class Node(threading.Thread):
    def __init__(self, addr, radio):
        super(Node, self).__init__()
        self.addr = addr
        self.radio = radio
        self.stack  = net.stack.Stack.create(addr, radio)
        self.daemon = True

        # Buffers for interprocess communication.
        self.incoming_buffer = queue.Queue()
        self.outgoing_buffer = queue.Queue()

    def send(self, data, dest_addr=None):
        self.stack.send(data, dest_addr)

    def process_incoming(self):
        while True:
            incoming = self.incoming_buffer.get()
            self.radio.put_incoming(incoming)

    def process_outgoing(self):
        while True:
            outgoing = self.radio.get_outgoing()
            self.outgoing_buffer.put(outgoing)

    def run(self):
        self.stack.start()
        t1 = threading.Thread(target=self.process_incoming)
        t2 = threading.Thread(target=self.process_outgoing)
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()

    @classmethod
    def create(cls, addr):
        radio = Radio(addr)
        return Node(addr, radio)
