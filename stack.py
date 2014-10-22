import threading


def process_incoming(layer1, layer2):
    while True:
        data = layer1.get_incoming()
        layer2.process_incoming(data)


def process_outgoing(layer1, layer2):
    while True:
        data = layer1.get_outgoing()
        layer2.process_outgoing(data)


class Stack(threading.Thread):
    def __init__(self):
        super(Stack, self).__init__()
        self.daemon = True
        self.layers = []

    def set_layers(self, layers):
        self.layers = layers

    def run(self):
        for index, layer in enumerate(self.layers):
            if index == (len(self.layers) - 1):
                continue
            layer1 = layer
            layer2 = self.layers[index + 1]
            incoming = threading.Thread(
                    target=process_incoming, args=(layer1, layer2))
            outgoing = threading.Thread(
                    target=process_outgoing, args=(layer2, layer1))
            incoming.setDaemon(True)
            outgoing.setDaemon(True)
            incoming.start()
            outgoing.start()
