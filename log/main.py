import argparse
import re

from utils import get_log_lines
from utils import get_nodes
from utils import get_stats
from utils import sync_timings


def main(args):
    lines = get_log_lines(args.files)

    # Split into runs
    runs = []
    current_idx = 0
    start_idx = 0
    while current_idx < len(lines):
        line = lines[current_idx]
        if (line.addr == 7 or line.addr == 20) and \
                line.protocol == "Deluge" and \
                "Starting Application" in line.message:
            runs.append(lines[start_idx:current_idx])
            start_idx = current_idx
        current_idx += 1
    runs.append(lines[start_idx:current_idx])

    # Eliminate runs without any DATA packets sent
    def is_protocol_simulation(run):
        if len(get_nodes(run)) <= 1:
            return False
        # First line should be "Starting application."
        if "Starting" not in run[0].original:
            return False
        # Number of DATA packets should be at least 100.
        num_data_packets = 0
        for lines in run:
            if "DATA" in lines.message:
                num_data_packets += 1
            if num_data_packets > 100:
                return True
        return False
    runs = filter(is_protocol_simulation, runs)
    print "Number of runs: %s" % len(runs)

    # Sync timings.
    if args.c:
        runs = map(sync_timings, runs)

    # Save to file.
    if args.o:
        for i in xrange(len(runs)):
            f = open('run-%s.log' % i, 'w')
            for line in runs[i]:
                f.write(line.original)
            f.close()

    for run in runs:
        get_stats(run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Logfile Parser')
    parser.add_argument('files', metavar='LOGFILE', nargs='+',
                        type=argparse.FileType('r'), help="Logfiles to parse.")
    parser.add_argument('-o', action='store_true', help="Output runs to file.")
    parser.add_argument('-c', action='store_true', help="Attempt to sync timings from multiple logfiles.")
    args = parser.parse_args()
    main(args)
