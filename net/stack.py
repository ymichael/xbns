from layers import transport
from layers import datalink
from layers import physical
from radio import xbeeradio

import argparse
import serial
import threading
import time


class Stack(threading.Thread):
    def __init__(self, addr, base_layers):
        super(Stack, self).__init__()
        self.daemon = True
        self.addr = addr
        self.base_layers = base_layers
        self.app_layers = {}

    def run(self):
        """Binds each layer to its previous and next layer.

        Starts listening on the respective queues.
        """
        for index, layer in enumerate(self.base_layers):
            incoming_layer = self.base_layers[index - 1] if index != 0 else None
            outgoing_layer = self.base_layers[index + 1] if \
                index != len(self.base_layers) - 1 else None
            layer.start(
                incoming_layer=incoming_layer,
                outgoing_layer=outgoing_layer)

    def add_app(self, app):
        assert app.get_port() not in self.app_layers
        self.app_layers[app.get_port()] = app
        app.set_addr(self.addr)

        # Register application with the transport layer.
        transport_layer = self.base_layers[-1]
        transport_layer.add_app(app)

        # Connect application to transport layer.
        app.start(incoming_layer=transport_layer)

    @classmethod
    def create(cls, addr, radio):
        # Default layers
        layers = [
            physical.Physical(radio),
            datalink.DataLink(),
            transport.Transport(),
        ]
        for l in layers:
            l.set_addr(addr)
        return Stack(addr, layers)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='XBee Test Networking Stack')
    parser.add_argument('-s', '--port', default='/dev/ttyUSB0',
                        help='Serial port')
    parser.add_argument('-b', '--baudrate', default=57600, type=int,
                        help='Baudrate')
    parser.add_argument('-m', '--myid', required=True, help='Module id, 16-bit')
    parser.add_argument('-p', '--panid', required=True,
                        help='Personal Area Network (PAN) id, 64-bit, eg. 0x1234')
    parser.add_argument('-c', '--channel', required=True,
                        help='Channel, 0x0B - 0x1A (11 - 26)')

    def string_to_int(int_or_hex):
        return int(int_or_hex, 16 if int_or_hex.startswith("0x") else 10)

    args = parser.parse_args()
    myid = string_to_int(args.myid)
    panid = string_to_int(args.panid)
    channel = string_to_int(args.channel)
    radio = xbeeradio.XBeeRadio.create(
        args.port, args.baudrate, panid, channel, myid)
    stack = Stack.create(myid, radio)
    stack.start()

    # TODO(michael): Stack doesn't do anything here, add application.
    while True:
        time.sleep(10)
