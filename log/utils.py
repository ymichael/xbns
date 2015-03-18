import collections
import datetime
import math
import re
import tabulate


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
    v_to_lines = collections.defaultdict(int)
    for l in lines:
        if l.version:
            v_to_lines[l.version] += 1
    return max(v_to_lines.keys(), key=lambda v: v_to_lines[v])


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

    # Breakdown of completion times for each node
    total_pages = next(l.total_pages for l in lines if l.version == version)
    completion_times = dict((n, dict()) for n in nodes)
    for page in xrange(total_pages + 1):
        for node in nodes:
            for line in lines:
                if line.addr == node and \
                        line.version == version and \
                        line.completed_pages >= page:
                    completion_times[node][page] = line.timestamp
                    break

    # Time taken for each node
    final_times = {}
    for n in nodes:
        if completion_times[n].get(total_pages):
            final_times[n] = completion_times[n][total_pages]
    time_taken = {}
    for node in nodes:
        if node in start_times and final_times.get(node) is not None:
            time_taken[node] = final_times[node] - start_times[node]
    seed_addrs = set(node for node, t in time_taken.iteritems() if t.total_seconds() == 0)

    # Packets sent by each node (between earliest start_time and latest completion_time)
    protocol_start = min(start_times.values())
    protocol_end = max(final_times.values())
    # 0: ADV, 1: REQ, 2: DATA
    packets_sent = dict((node, [0, 0, 0]) for node in nodes)
    for line in lines:
        if line.addr and protocol_start <= line.timestamp <= protocol_end and \
                "Sending message" in line.message:
            # Extract message size to determine number of frames sent.
            size = int(re.match(".*Sending message \((.*?)\):.*", line.message).groups()[0])
            frames = math.ceil(size / 80.0)
            if "ADV" in line.original:
                packets_sent[line.addr][0] += frames
            elif "REQ" in line.original:
                packets_sent[line.addr][1] += frames
            elif "DATA" in line.original:
                packets_sent[line.addr][2] += frames


    print "#####################################################################"
    print "Run starting %s" % lines[0].timestamp.strftime("%Y-%m-%d %H:%M:%S,%f")
    print "#####################################################################"
    print "Nodes involved %s" % nodes
    print "Seed = %s, T_MIN = %s" % (seed_addrs, t_min)
    print "# Start/Completion/Total times"
    ppprint_timings(start_times, final_times, time_taken)
    print "# Completion times (breakdown, secs after seed start time.)"
    pprint_completion_times(completion_times)
    print "# Packets sent"
    pprint_packets_sent(packets_sent)


def ppprint_timings(start_times, final_times, time_taken):
    order = [node for t, node in sorted((t, node) for node, t in time_taken.iteritems())]
    rows = []
    for node in order:
        row = [node]
        row.append(start_times.get(node))
        row.append(final_times.get(node))
        row.append(time_taken.get(node))
        rows.append(row)
    headers = ["node", "start", "end", "time taken"]
    print tabulate.tabulate(rows, headers=headers, numalign="right", stralign="right")


def pprint_packets_sent(packets_sent):
    nodes = packets_sent.keys()
    rows = []
    for n in nodes:
        row = [n]
        row.extend(packets_sent[n])
        row.append(sum(packets_sent[n]))
        rows.append(row)

    # second last row
    second_last_row = ["total"]
    for i in xrange(len(rows[0])):
        if i == 0: continue
        second_last_row.append(sum(r[i] for r in rows))
    rows.append(second_last_row)

    # last row
    last_row = ["percent"]
    for i in xrange(len(second_last_row)):
        if i == 0: continue
        last_row.append("%.2f%%" % (100 * second_last_row[i] / second_last_row[-1]))
    rows.append(last_row)
    print tabulate.tabulate(
        rows, headers=["node", "ADV", "REQ", "DATA", "Total"],
        numalign="right", stralign="right")


def pprint_completion_times(ct):
    nodes = ct.keys()
    total_pages = len(ct[nodes[0]]) - 1

    # Get seed.
    start_times = {}
    for n in nodes:
        if ct[n].get(0):
            start_times[n] = ct[n][0]
    nodes = sorted(start_times.keys(), key=lambda n: start_times.get(n))
    seed = nodes[0]

    # Order events to better visualize pipelining.
    events = []
    time_elapsed = {}
    for page in xrange(total_pages + 1):
        for node in nodes:
            t = (ct[node][page] - ct[seed][0]).total_seconds()
            # Round unless we get 0, then take the ceiling.
            t = round(t) or math.ceil(t)
            events.append((t, node, page))
    events.sort()

    for i in xrange(len(events)):
        t, node, page = events[i]
        # store a 2 element list (time_elapsed, event_order)
        time_elapsed[(node, page)] = [t, i]

    # Sort nodes by (page0, page1, ...)
    def key_func(n):
        return [time_elapsed[(n, p)][0] for p in xrange(total_pages + 1)]
    nodes = sorted(nodes, key=key_func)

    rows = []
    for page in xrange(total_pages + 1):
        row = [page]
        for node in nodes:
            t, order = time_elapsed[(node, page)]
            # row.append("%d, (%s)" % (t, order))
            row.append("%d" % t)
        rows.append(row)

    headers = ['page no.']
    headers.extend(nodes)
    print tabulate.tabulate(rows, headers=headers, numalign="right", stralign="right")


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
        # TODO: Investigate bug 16 mar where version goes crazy.
        if logline.version and logline.version > 100:
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
