from layers import application
from layers import datalink
from layers import physical
from radio import xbeeradio

import argparse
import serial
import threading
import time


class Stack(threading.Thread):
    def __init__(self, addr, layers):
        super(Stack, self).__init__()
        self.addr = addr
        self.daemon = True
        self.layers = layers

    def run(self):
        """Binds each layer to its previous and next layer.

        Starts listening on the respective queues.
        """
        for index, layer in enumerate(self.layers):
            incoming_layer = self.layers[index - 1] if index != 0 else None
            outgoing_layer = self.layers[index + 1] if \
                index != len(self.layers) - 1 else None
            layer.start(
                incoming_layer=incoming_layer,
                outgoing_layer=outgoing_layer)

    def send(self, data, dest_addr=None):
        self.layers[-1].send(data, dest_addr)

    @classmethod
    def create(cls, addr, radio, additional_layers=None):
        # Configure the physical layer.
        physical_layer = physical.Physical(radio)
        # Default layers
        layers = [
            physical_layer,
            datalink.DataLink(),
            application.Application(),
        ]
        if additional_layers is not None:
            for l in additional_layers:
                layers.append(l)

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
    while True:
        time.sleep(1)
        stack.send("0" * 1000)
