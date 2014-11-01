from collections import defaultdict
import threading


class Network(threading.Thread):
    def __init__(self):
        super(Network, self).__init__()
        self.outgoing_links = defaultdict(set)
        self.radios = {}

    def _add_link(self, a, b):
        """Adds an outgoing link from `a` to `b`."""
        self.outgoing_links[a].add(b)

    def add_radio(self, radio, outgoing_links):
        self.radios[radio.addr] = radio
        for link in outgoing_links:
            self._add_link(radio.addr, link)

    def broadcast(self, data, a):
        """Broadcast data from `a`."""
        # Radios expect a tuple of (data, sender_addr)
        frame = (data, a)
        for dest in self.outgoing_links[a]:
            self._send(frame, dest)

    def process_messages(self, addr):
        while True:
            outgoing_message = self.radios[addr].get_outgoing()
            self.broadcast(outgoing_message, addr)

    def run(self):
        for addr in self.radios.keys():
            t = threading.Thread(target=self.process_messages, args=(addr,))
            t.setDaemon(True)
            t.start()

    def _send(self, frame, b):
        """Sends a frame to `b`."""
        radio = self.radios[b]
        radio.put_incoming(frame)
