from radio import Radio
import Queue as queue
import net.stack
import threading


class Node(threading.Thread):
    def __init__(self, addr, radio):
        super(Node, self).__init__()
        self.daemon = True

        self.addr = addr
        self.radio = radio
        self.stack  = net.stack.Stack.create(addr, radio)

        # Buffers for inter-node communication.
        self.incoming_buffer = queue.Queue()
        self.outgoing_buffer = queue.Queue()

        # Applications running on this node.
        # "application name" => <application instance>
        self.apps = {}

    def add_app(self, app):
        assert app.get_port() not in self.apps
        self.apps[app.get_port()] = app
        self.stack.add_app(app)

    def get_app(self, port_no):
        return self.apps[port_no]

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
