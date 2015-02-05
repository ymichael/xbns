#!/usr/bin/env python

import argparse
import config
import net.radio.xbeeradio
import time


def main(args):
    def string_to_int(int_or_hex):
        return int(int_or_hex, 16 if int_or_hex.startswith("0x") else 10)

    myid = string_to_int(args.myid) if args.myid else config.ADDR
    panid = string_to_int(args.panid) if args.panid else config.PANID
    channel = string_to_int(args.channel) if args.channel else config.CHANNEL
    xbeeradio = net.radio.xbeeradio.XBeeRadio.create(
        args.port, args.baudrate, panid, channel, myid)

    while True:
        frame = xbeeradio.xbee_module.wait_read_frame()
        print frame


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Troubleshoot xbee.')
    # XBee Configuration
    parser.add_argument('-s', '--port', default='/dev/ttyUSB0',
                        help='Serial port')
    parser.add_argument('-b', '--baudrate', default=57600, type=int,
                        help='Baudrate')
    parser.add_argument('-m', '--myid', help='Module id, 16-bit')
    parser.add_argument('-p', '--panid',
                        help='Personal Area Network (PAN) id, 64-bit, eg. 0x1234')
    parser.add_argument('-c', '--channel', help='Channel, 0x0B - 0x1A (11 - 26)')
    main(parser.parse_args())
