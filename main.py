import argparse
import layers
import serial
import stack
import time
import xbee
import Queue as queue


def string_to_int(int_or_hex):
    return int(int_or_hex, 16 if int_or_hex.startswith("0x") else 10)

def main(args):
    myid = string_to_int(args.myid)
    panid = string_to_int(args.panid)
    channel = string_to_int(args.channel)

    if not (0 <= myid <= 2**16):
        raise ValueError("Expected 16-bit Module Id, got: %s" % args.myid)
    if not (0 <= panid < 2**64):
        raise ValueError("Expected 64-bit PAN id, got: %s" % args.panid)
    if not (11 <= channel <= 26):
        raise ValueError("Expected Channel id between 11 and 26, got: %s" % args.channel)

    # Configure the physical layer.
    serial_object = serial.Serial(args.port, args.baudrate)
    xbee_module = xbee.XBee(serial_object)
    physical_layer = layers.physical.Physical(xbee_module)
    physical_layer.set_myid(myid)
    physical_layer.set_panid(panid)
    physical_layer.set_channel(channel)

    # Other layers.
    datalink_layer = layers.datalink.DataLink()
    network_layer = layers.network.Network(myid)
    transport_layer = layers.transport.Transport()
    application_layer = layers.application.Application()

    # Start networking stack.
    networking_stack = stack.Stack()
    networking_stack.set_layers([
        physical_layer,
        datalink_layer,
        network_layer,
        transport_layer,
        application_layer,
    ])

    try:
        networking_stack.start()
        while True:
            time.sleep(1)
            application_layer.send("0" * 1000)
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='XBee Network')
    parser.add_argument('-s', '--port', default='/dev/ttyUSB0',
                        help='Serial port')
    parser.add_argument('-b', '--baudrate', default=57600, type=int,
                        help='Baudrate')
    parser.add_argument('-m', '--myid', required=True, help='Module id, 16-bit')
    parser.add_argument('-p', '--panid', required=True,
                        help='Personal Area Network (PAN) id, 64-bit, eg. 0x1234')
    parser.add_argument('-c', '--channel', required=True,
                        help='Channel, 0x0B - 0x1A (11 - 26)')
    main(parser.parse_args())
