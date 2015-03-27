import argparse
import os.path
import re
import tabulate

from utils import get_log_lines
from utils import get_nodes
from utils import get_stats
from utils import get_version
from utils import sync_timings


def main(args):
    lines = get_log_lines(args.files)

    # Split into sorted lists for each node.
    nodes = get_nodes(lines)
    node_to_lines = {}
    node_to_runs = {}
    for n in nodes:
        node_to_lines[n] = sorted(filter(lambda l: l.addr == n, lines))
        # Split by Manager lines.
        runs = []
        current_idx = 0
        start_idx = 0
        while current_idx < len(node_to_lines[n]):
            if node_to_lines[n][current_idx].protocol == "Manager":
                runs.append(node_to_lines[n][start_idx:current_idx])
                start_idx = current_idx
            current_idx += 1
        runs.append(node_to_lines[n][start_idx:current_idx])
        node_to_runs[n] = filter(lambda r: len(r) > 100, runs)
    
    # Use 20 as the anchor
    runs = []
    for i, r in enumerate(node_to_runs[20]):
        run = {}
        run[20] = i
        start = r[0].timestamp
        for n in nodes:
            if n == 20:
                continue
            for j, r in enumerate(node_to_runs[n]):
                if abs((start - r[0].timestamp).total_seconds()) < 90:
                    run[n] = j
        runs.append(run)
    rows = []
    for i, r in enumerate(runs):
        row = [i]
        for n in nodes:
            idx = r.get(n)
            timestamp = node_to_runs[n][idx][0].timestamp if idx else None
            row.append("%s, %s" % (idx, timestamp))
        rows.append(row)

    header = ["run"]
    for n in nodes:
        header.append(n)
    print tabulate.tabulate(rows, headers=header)

    # Merge runs.
    if args.o:
        for i in xrange(len(runs)):
            run = []
            for n, idx in runs[i].iteritems():
                run.extend(node_to_runs[n][idx])
            f = open('run-%s.log' % i, 'w')
            for line in sorted(run):
                f.write(line.original)
                f.write("\n")
            f.close()
    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Expt Logfile Parser')
    parser.add_argument('files', metavar='LOGFILE', nargs='+',
                        type=argparse.FileType('r'), help="Logfiles to parse.")
    parser.add_argument('-o', action='store_true', help="Output runs to file.")
    parser.add_argument('-c', action='store_true', help="Attempt to sync timings from multiple logfiles.")
    args = parser.parse_args()
    main(args)
