import argparse
import re

from utils import get_log_lines
from utils import sync_timings


def main(args):
    lines = get_log_lines(args.files)

    # Filter lines.
    if args.s is not None:
        lines = filter(lambda x: x.addr in args.s and "Sending" in x.original, lines)
    if args.r is not None:
        lines = filter(lambda x: x.addr in args.r and "Received" in x.original, lines)

    if args.c:
        lines = sync_timings(lines)

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
    parser.add_argument('-c', action='store_true', help="Attempt to sync timings.")
    args = parser.parse_args()
    main(args)
