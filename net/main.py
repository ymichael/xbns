#!/usr/bin/env python

import argparse
import layers.datalink
import layers.physical
import layers.transport
import radio.xbeeradio
import time


def main(args):
    def string_to_int(int_or_hex):
        return int(int_or_hex, 16 if int_or_hex.startswith("0x") else 10)

    # Set up and configure XBee Radio.
    myid = string_to_int(args.myid)
    addr = myid
    panid = string_to_int(args.panid)
    channel = string_to_int(args.channel)
    xbeeradio = radio.xbeeradio.XBeeRadio.create(
        args.port, args.baudrate, panid, channel, myid)

    # Create layers.
    physical = layers.physical.Physical(addr, xbeeradio)
    datalink = layers.datalink.DataLink(addr)
    transport = layers.transport.Transport(addr)

    # Start up Physical layer.
    # - listen for incoming packets on the radio
    physical.start_listen_to_radio()
    # - handle outgoing packets from DataLink layer
    physical.start_handling_outgoing(datalink.get_outgoing_queue())

    # Start up DataLink layer.
    # - handle incoming packets from Physical layer
    datalink.start_handling_incoming(physical.get_incoming_queue())
    # - handle outgoing packets from Transport layer
    datalink.start_handling_outgoing(transport.get_outgoing_queue())

    # Start up Transport layer.
    # - handle incoming packets from DataLink layer
    transport.start_handling_incoming(datalink.get_incoming_queue())
    # - handle outgoing packets from various Applications
    transport.start_handling_outgoing(transport.get_outgoing_socket_reader())

    while True:
        time.sleep(10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='XBee Network Stack')
    # XBee Configuration
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
