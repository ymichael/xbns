#!/usr/bin/env python

import argparse
import config
import layers.datalink
import layers.physical
import layers.transport
import radio.xbeeradio
import time


def main(args):
    def string_to_int(int_or_hex):
        return int(int_or_hex, 16 if int_or_hex.startswith("0x") else 10)

    if args.myid:
        myid = string_to_int(args.myid)
    else:
        myid = config.ADDR
    addr = myid

    if args.panid:
        panid = string_to_int(args.panid)
    else:
        panid = config.PANID

    if args.channel:
        channel = string_to_int(args.channel)
    else:
        channel = config.CHANNEL

    # Set up and configure XBee Radio.
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
    parser.add_argument('-m', '--myid', help='Module id, 16-bit')
    parser.add_argument('--power', type=int, default=4, choices=[0,1,2,3,4],
                        help='Power level of xbee.')
    parser.add_argument('-p', '--panid',
                        help='Personal Area Network (PAN) id, 64-bit, eg. 0x1234')
    parser.add_argument('-c', '--channel', help='Channel, 0x0B - 0x1A (11 - 26)')
    main(parser.parse_args())
