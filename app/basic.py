import net.layers.application


class Basic(net.layers.application.Application):
    def __init__(self, port):
        super(Basic, self).__init__()
        self.port = port

    def get_port(self):
        return self.port