import threading


class Stack(threading.Thread):
    def __init__(self):
        super(Stack, self).__init__()
        self.daemon = True
        self.layers = []

    def set_layers(self, layers):
        self.layers = layers

    def run(self):
        """Binds each layer to its previous and next layer.

        Starts listening on the respective queues."""
        for index, layer in enumerate(self.layers):
            incoming_layer = self.layers[index - 1] if index != 0 else None
            outgoing_layer = self.layers[index + 1] if \
                index != len(self.layers) - 1 else None
            layer.start(
                incoming_layer=incoming_layer,
                outgoing_layer=outgoing_layer)
