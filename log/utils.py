import collections
import datetime
import math
import re


class LogLine(object):
    def __init__(self, timestamp, log_level, protocol, message, original,
            addr=None, state=None, version=None, completed_pages=None,
            total_pages=None, t=None, pdu=None, pdu_source_addr=None,
            pdu_repr=None):
        self.timestamp = timestamp
        self.log_level = log_level
        self.protocol = protocol
        self.message = message
        self.original = original
        self.addr = addr
        self.state = state
        self.version = version
        self.completed_pages = completed_pages
        self.total_pages = total_pages
        self.t = t
        self.pdu = pdu
        self.pdu_source_addr = pdu_source_addr
        self.pdu_repr = pdu_repr

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __gt__(self, other):
        return self.timestamp > other.timestamp

    def __ge__(self, other):
        return self.timestamp >= other.timestamp

    def __le__(self, other):
        return self.timestamp <= other.timestamp


def parse_log_line(line):
    """Takes a line from the logs and attempts to parse it."""
    # Prefix format.
    # %(name)s - %(levelname)s - %(asctime)s: %(message)s
    matches = re.match("(.*?) - (.*?) - ([0-9\-:,\s]*):(.*)", line)
    if matches is None:
        return None
    groups = matches.groups()
    protocol = groups[0]
    log_level = groups[1]
    message = groups[3].strip()

    # 2014-04-23 20:20:04,607
    # timestamp = datetime.datetime.strptime(groups[2], "%Y-%m-%d %H:%M:%S,%f")
    # year, month, day, h, m, s, micros = \
    #     re.match("([0-9]*?)-([0-9]*?)-([0-9]*?) ([0-9]*?):([0-9]*?):([0-9]*?),([0-9]*)", timestamp).groups()
    # This is 2X faster that strptime and slightly better than using re.
    timestamp = groups[2].strip()
    date, time = timestamp.split()
    year, month, day = date.split("-")
    time, micros = time.split(",")
    h, m, s = time.split(":")
    timestamp = datetime.datetime(int(year), int(month), int(day), int(h), int(m), int(s), int(micros))

    # Try to parse message
    msg_matches = re.match("\((.*?), (.*?), \[v(.*?), (.*?)\/(.*?)\], (.*?)\) - (.*)", message)
    if msg_matches is None:
        return LogLine(timestamp=timestamp, log_level=log_level, original=line,
                       protocol=protocol, message=message)

    msg_groups = msg_matches.groups()
    addr = int(msg_groups[0])
    state = msg_groups[1]
    version = int(msg_groups[2])
    completed_pages = int(msg_groups[3])
    total_pages = int(msg_groups[4])
    t = float(msg_groups[5])
    pdu = msg_groups[6]

    # Try to parse pdu.
    if "Received message" in pdu:
        # eg. Received message from <X>: <PDU>
        pdu_matches =  re.match("Received message from (.*?): (.*)", pdu)
        pdu_groups = pdu_matches.groups()
        source_addr = int(pdu_groups[0])
        pdu_repr = pdu_groups[1]
    elif "Sending message" in pdu:
        # eg. Sending message (X): <PDU>
        pdu_matches =  re.match("Sending message \(.*?\): (.*)", pdu)
        pdu_groups = pdu_matches.groups()
        # Self is the source.
        source_addr = addr
        pdu_repr = pdu_groups[0]
    else:
        source_addr = None
        pdu_repr = None

    return LogLine(timestamp=timestamp, log_level=log_level,
                   protocol=protocol, message=message, original=line,
                   addr=addr, state=state, version=version,
                   completed_pages=completed_pages, total_pages=total_pages,
                   t=t, pdu=pdu, pdu_source_addr=source_addr,
                   pdu_repr=pdu_repr)


def get_nodes(lines):
    return set(line.addr for line in lines if line.addr)

def get_version(lines):
    return max(line.version for line in lines if line.version)

def get_stats(lines):
    # Nodes involved and version upgraded to.
    nodes = get_nodes(lines)
    version = get_version(lines)

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


def sync_timings(lines):
    nodes = get_nodes(lines)
    version = get_version(lines)
    deltas = dict((n, datetime.timedelta()) for n in nodes)

    # Get the first message received from every other node
    for node in nodes:
        for node2 in nodes:
            if node == node2:
                continue

            first_message_received = None
            for l in lines:
                if l.addr == node and l.version == version and \
                        l.pdu_source_addr != None and l.pdu_source_addr == node2:
                    first_message_received = l
                    break
            if first_message_received is None:
                continue

            sender = node2
            pdu_repr = first_message_received.pdu_repr.strip()

            # Search for first possible sent log
            first_message_sent = None
            for l in lines:
                if l.addr == sender and l.pdu_source_addr == sender and \
                        l.pdu_repr and l.pdu_repr == pdu_repr:
                    first_message_sent = l
                    break
            if first_message_sent is None:
                continue

            # Correct the timings
            if first_message_sent.timestamp > first_message_received.timestamp:
                # Always correct sender to earlier timing.
                delta = first_message_sent.timestamp - first_message_received.timestamp
                # Add a small transmission delay
                delta += datetime.timedelta(milliseconds=10)
                deltas[sender] = max(delta, deltas[sender])

    def correct_timing(l):
        if l.addr is None or deltas[l.addr] == 0:
            return l
        else:
            l.timestamp -= deltas[l.addr]
            return l

    lines = map(correct_timing, lines)
    lines.sort()
    return lines


def get_log_lines(files):
    lines = []

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
    for f in files:
        lines.extend(filter(is_relevant, map(parse_log_line, f.readlines())))

    lines.sort()
    return lines