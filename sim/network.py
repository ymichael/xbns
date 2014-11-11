from collections import defaultdict
import threading
import time


class Network(threading.Thread):
    def __init__(self, delay=.01):
        super(Network, self).__init__()
        self.outgoing_links = defaultdict(set)
        self.nodes = {}
        self.daemon = True
        self.delay = delay

    def _add_link(self, a, b):
        """Adds an outgoing link from `a` to `b`."""
        self.outgoing_links[a].add(b)

    def add_node(self, node, outgoing_links):
        self.nodes[node.addr] = node
        for link in outgoing_links:
            self._add_link(node.addr, link)

    def broadcast(self, data, a):
        """Broadcast data from `a`."""
        # Radios expect a tuple of (data, sender_addr)
        time.sleep(self.delay)
        frame = (data, a)
        for dest in self.outgoing_links[a]:
            self.nodes[dest].incoming_buffer.put(frame)

    def process_outgoing(self, addr):
        while True:
            outgoing_message = self.nodes[addr].outgoing_buffer.get()
            self.broadcast(outgoing_message, addr)

    def run(self):
        for addr, node in self.nodes.iteritems():
            t = threading.Thread(target=self.process_outgoing, args=(addr,))
            t.setDaemon(True)
            t.start()
            node.start()
