import argparse
import math
import re

from utils import parse_log_line


def main(args):
    def is_relevant(logline):
        if logline is None:
            return False
        if logline.timestamp.year != 2015:
            return False
        return True

    # Read lines each logfile into a list.
    lines = []
    for f in args.files:
        lines.extend(filter(is_relevant, map(parse_log_line, f.readlines())))
    lines.sort()

    # Filter lines.
    if args.s is not None:
        lines = filter(lambda x: x.addr in args.s and "Sending" in x.original, lines)
    if args.r is not None:
        lines = filter(lambda x: x.addr in args.r and "Received" in x.original, lines)

    for line in lines:
        print line.original.strip()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Logfile Filter')
    parser.add_argument('files', metavar='LOGFILE', nargs='+',
                        type=argparse.FileType('r'), help="Logfiles to filter.")
    parser.add_argument('-s', action='append', type=int,
                        help="Only show logs for messages sent from these nodes")
    parser.add_argument('-r', action='append', type=int,
                        help="Only show logs for messages received by these nodes")
    args = parser.parse_args()
    main(args)
