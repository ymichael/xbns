import collections
import datetime
import math
import re
import tabulate


class LogLine(object):
    __slots__ = [
        "timestamp",
        "log_level",
        "protocol",
        "message",
        "original",
        "addr",
        "state",
        "version",
        "completed_pages",
        "total_pages",
        "t",
        "pdu",
        "pdu_source_addr",
        "pdu_repr",
    ]

    def __init__(self, timestamp, log_level, protocol, message, original):
        self.timestamp = timestamp
        self.log_level = log_level
        self.protocol = protocol
        self.message = message
        self.original = original

        self.addr = None
        self.state = None
        self.version = None
        self.completed_pages = None
        self.total_pages = None
        self.t = None
        self.pdu = None
        self.pdu_source_addr = None
        self.pdu_repr = None

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __gt__(self, other):
        return self.timestamp > other.timestamp

    def __ge__(self, other):
        return self.timestamp >= other.timestamp

    def __le__(self, other):
        return self.timestamp <= other.timestamp


LOG_PREFIX_RE = re.compile("(.*?) - (.*?) - ([0-9\-:,\s]*):(.*)")
DELUGE_PREFIX_RE = re.compile("\((.*?), (.*?), \[v(.*?), (.*?)\/(.*?)\], (.*?)\) - (.*)")
MANAGER_PREFIX_RE = re.compile("\((.*?), (.*?), D=(.*?), R=(.*?), k = (.*?), t_min = (.*?), t_max = (.*?), delay = (.*?)\) - (.*)")
RECEIVE_PDU_PREFIX_RE = re.compile("Received message from (.*?): (.*)")
SEND_PDU_PREFIX_RE = re.compile("Sending message \(.*?\): (.*)")


def parse_log_line(line):
    """Takes a line from the logs and attempts to parse it."""
    # Prefix format.
    # %(name)s - %(levelname)s - %(asctime)s: %(message)s
    matches = LOG_PREFIX_RE.match(line)
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

    logline = LogLine(timestamp, log_level, protocol, message, line.strip())
    # Try to parse message
    # Deluge/Rateless prefix:
    # eg. RatelessDeluge - INFO - 2015-03-12 16:38:17,096: (20,  MAIN, [v0, 00/00],  600) - Application started!
    msg_matches = DELUGE_PREFIX_RE.match(message)
    if msg_matches is not None:
        msg_groups = msg_matches.groups()
        logline.addr = int(msg_groups[0])
        logline.state = msg_groups[1]
        logline.version = int(msg_groups[2])
        logline.completed_pages = int(msg_groups[3])
        logline.total_pages = int(msg_groups[4])
        logline.t = float(msg_groups[5])
        logline.pdu = msg_groups[6].strip()

    # Try to parse manager prefix
    # eg. Manager - INFO - 2015-03-12 16:38:18,944: ( 6, rateless, D=1020/60, R=1200/120,
    #     k = 1, t_min = 1, t_max = 600, delay = 3) - Received message ...
    # msg_matches = MANAGER_PREFIX_RE.match(message)
    if protocol == "Manager":
        message_parts = message.split(" - ")
        # ('11', 'deluge', '6000/60', '900/45', '1', '4.0', '600', '3', 'Sending message (1): ACK')
        # msg_groups = msg_matches.groups()
        # logline.addr = int(msg_groups[0])
        # logline.pdu = msg_groups[8]
        if "(" in message and "," in message:
            logline.addr = int(message[message.index("(") + 1:message.index(",")])
            logline.pdu = message_parts[-1]

    # Try to parse pdu: (Deluge/Rateless/Manager).
    if logline.pdu and "Received message" in logline.pdu:
        # eg. Received message from <X>: <PDU>
        # pdu_matches =  RECEIVE_PDU_PREFIX_RE.match(logline.pdu)
        # pdu_groups = pdu_matches.groups()
        # logline.pdu_source_addr = int(pdu_groups[0])
        # logline.pdu_repr = pdu_groups[1]
        logline.pdu_source_addr = int(logline.pdu[21:logline.pdu.index(":")])
        logline.pdu_repr = logline.pdu[logline.pdu.index(":") + 1:]

    if logline.pdu and "Sending message" in logline.pdu:
        # eg. Sending message (X): <PDU>
        # pdu_matches =  SEND_PDU_PREFIX_RE.match(logline.pdu)
        # pdu_groups = pdu_matches.groups()
        # logline.pdu_repr = pdu_groups[0]
        logline.pdu_source_addr = logline.addr
        logline.pdu_repr = logline.pdu[logline.pdu.index(":") + 1:]

    return logline


def get_nodes(lines):
    return set(line.addr for line in lines if line.addr)


def get_version(lines):
    v_to_lines = collections.defaultdict(int)
    for l in lines:
        if l.version:
            v_to_lines[l.version] += 1
    return max(v_to_lines.keys(), key=lambda v: v_to_lines[v])


def get_total_pages(lines, version=None):
    version = version or get_version(lines)
    return max(l.total_pages for l in lines if l.version == version)


def get_t_min(lines):
    # Determine the T_MIN and the seed node for this run.
    return min(line.t for line in lines if line.t)


def get_start_times(lines, nodes=None, t_min=None):
    nodes = nodes or get_nodes(lines)
    t_min = t_min or get_t_min(lines)
    start_times = {}
    for node in nodes:
        for line in lines:
            if line.addr == node and line.t == t_min:
                start_times[node] = line.timestamp
                break
    return start_times


def get_completion_times(lines, nodes=None, total_pages=None, version=None):
    version = version or get_version(lines)
    nodes = nodes or get_nodes(nodes)
    total_pages = get_total_pages(lines, version)
    # Breakdown of completion times for each node
    completion_times = dict((n, dict()) for n in nodes)
    for page in xrange(total_pages + 1):
        for node in nodes:
            for line in lines:
                if line.addr == node and \
                        line.version == version and \
                        line.completed_pages >= page:
                    completion_times[node][page] = line.timestamp
                    break
    return completion_times


def get_final_times(lines, nodes=None, total_pages=None, version=None):
    version = version or get_version(lines)
    nodes = nodes or get_nodes(nodes)
    total_pages = get_total_pages(lines, version)
    final_times = {}
    for node in nodes:
        for line in lines:
            if line.addr == node and \
                    line.version == version and \
                    line.completed_pages >= total_pages:
                final_times[node] = line.timestamp
                break
    return final_times


def get_time_taken(nodes, start_times, final_times):
    time_taken = {}
    for node in nodes:
        if node in start_times and final_times.get(node) is not None:
            time_taken[node] = final_times[node] - start_times[node]
    return time_taken


def get_seeds(time_taken):
    return set(node for node, t in time_taken.iteritems() if t.total_seconds() == 0)


def get_stats(lines):
    # Nodes involved and version upgraded to.
    nodes = get_nodes(lines)
    version = get_version(lines)
    t_min = get_t_min(lines)
    total_pages = get_total_pages(lines, version)

    start_times = get_start_times(lines, nodes, t_min)
    completion_times = get_completion_times(lines, nodes, total_pages, version)
    final_times = get_final_times(lines, nodes, total_pages, version)
    time_taken = get_time_taken(nodes, start_times, final_times)
    seeds = get_seeds(time_taken)

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
    print "Seed = %s, T_MIN = %s" % (seeds, t_min)
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
    total_pages = get_total_pages(lines, version)

    # Get seeds.
    t_min = get_t_min(lines)
    start_times = get_start_times(lines, nodes, t_min)
    final_times = get_final_times(lines, nodes, total_pages, version)
    time_taken = get_time_taken(nodes, start_times, final_times)
    seeds = get_seeds(time_taken)

    for seed in seeds:
        for node in nodes:
            if node in seeds:
                continue
            delta = datetime.timedelta()
            sender = seed
            receiver = node
            # Get messages received by receiver from sender at 10s interval.
            messages_received = []
            for l in lines:
                if not (l.addr == receiver and l.pdu_source_addr == sender):
                    continue
                if len(messages_received) == 0:
                    messages_received.append(l)
                elif abs((l.timestamp - messages_received[-1].timestamp).total_seconds()) > 10:
                    messages_received.append(l)
            # Find corresponding send messages.
            for message_received in messages_received:
                message_sent = None
                for l in lines:
                    if not (l.addr == sender and l.pdu_source_addr == sender):
                        continue
                    if l.pdu_repr.strip() != message_received.pdu_repr.strip():
                        continue
                    if message_sent is None:
                        message_sent = l
                    curr_delta = (message_sent.timestamp - message_received.timestamp).total_seconds()
                    new_delta = (l.timestamp - message_received.timestamp).total_seconds()
                    if abs(curr_delta) > abs(new_delta):
                        message_sent = l
                    else:
                        break
                # Correct the timings
                if message_sent and message_sent.timestamp > message_received.timestamp:
                    # Always correct sender to earlier timing.
                    new_delta = message_sent.timestamp - message_received.timestamp
                    new_delta += datetime.timedelta(milliseconds=10)
                    delta = max(delta, new_delta)

            updated_lines = []
            for l in lines:
                if l.addr == sender:
                    l.timestamp -= delta
                updated_lines.append(l)
            lines = sorted(updated_lines)

    return lines


def get_log_lines(files):
    lines = []

    def is_relevant(logline):
        if logline is None:
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
