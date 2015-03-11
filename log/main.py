import argparse
import math
import re

from utils import parse_log_line


def main(args):
    def is_relevant(logline):
        if logline is None:
            return False
        if logline.protocol == "Manager" and "CTRL" not in logline.original:
            return False
        if logline.timestamp.year != 2015:
            return False
        return True

    # Read lines each logfile into a list.
    lines = []
    for f in args.files:
        lines.extend(filter(is_relevant, map(parse_log_line, f.readlines())))
    lines.sort()

    # Split into runs
    runs = []
    current_idx = 0
    start_idx = 0
    while current_idx < len(lines):
        line = lines[current_idx]
        if line.addr == 20 and line.protocol == "Deluge" and \
                "Starting Application" in line.message:
            runs.append(lines[start_idx:current_idx])
            start_idx = current_idx
        current_idx += 1
    runs.append(lines[start_idx:current_idx])


    # Eliminate runs without any DATA packets sent
    def is_protocol_simulation(run):
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

    # Save to file.
    if args.o:
        for i in xrange(len(runs)):
            f = open('run-%s.log' % i, 'w')
            for line in runs[i]:
                f.write(line.original)
            f.close()

    for run in runs:
        get_stats(run)


def get_stats(lines):
    # Nodes involved and version upgraded to.
    nodes = set(line.addr for line in lines if line.addr)
    version = max(line.version for line in lines if line.version)

    # Determine the T_MIN and the seed node for this run.
    t_min = min(line.t for line in lines if line.t)

    # Start time (first message that indicated inconsistency) for each node
    start_times = {}
    for node in nodes:
        for line in lines:
            if line.addr == node and line.t == t_min:
                start_times[node] = line.timestamp
                break

    # Completion time for each node
    completion_times = {}
    for node in nodes:
        for line in lines:
            if line.addr == node and line.version == version and \
                    line.total_pages == line.completed_pages:
                completion_times[node] = line.timestamp
                break

    # Time taken for each node
    time_taken = {}
    for node in nodes:
        if node in start_times and node in completion_times:
            time_taken[node] = completion_times[node] - start_times[node]
    seed_addrs = set(node for node, t in time_taken.iteritems() if t.total_seconds() == 0)

    # Packets sent by each node (between earliest start_time and latest completion_time)
    protocol_start = min(start_times.values())
    protocol_end = max(completion_times.values())
    packets_sent = dict((node, 0) for node in nodes)
    for line in lines:
        if protocol_start <= line.timestamp <= protocol_end and \
                "Sending message" in line.message:
            # Extract message size to determine number of frames sent.
            size = int(re.match(".*Sending message \((.*?)\):.*", line.message).groups()[0])
            packets_sent[line.addr] += math.ceil(size / 80.0)

    # Packets received by each node (?)
    # Packet loss rate.
    print "#####################################################################"
    print "Run starting %s" % lines[0].timestamp.strftime("%Y-%m-%d %H:%M:%S,%f")
    print "#####################################################################"
    print "Nodes involved %s" % nodes
    print "Seed = %s, T_MIN = %s" % (seed_addrs, t_min)
    # Sort by distance from seed.
    order = [node for t, node in sorted((t, node) for node, t in time_taken.iteritems())]

    def ppprint(nodes_to_times):
        previous = None
        for node in order:
            if node not in start_times:
                continue
            delta = nodes_to_times[node] - previous if previous is not None else 0
            print "%s -> %s, (%s)" % (node, nodes_to_times[node], delta)
            previous = nodes_to_times[node]

    print "# Start times"
    ppprint(start_times)

    print "# Completion times"
    ppprint(completion_times)

    print "# Time taken"
    ppprint(time_taken)

    print "# Packets sent"
    for node in order:
        print node, "->", packets_sent[node] if node in packets_sent else None
    print "Total frames sent %s" % sum(packets_sent.values())




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Logfile Parser')
    parser.add_argument('files', metavar='LOGFILE', nargs='+',
                        type=argparse.FileType('r'), help="Logfiles to parse.")
    parser.add_argument('-o', action='store_true', help="Output runs to file.")
    args = parser.parse_args()
    main(args)
