import collections
import datetime
import re


_LogLine = collections.namedtuple(
    'LogLine',
    'timestamp log_level protocol message original addr state version completed_pages total_pages t pdu')


def LogLine(timestamp, log_level, protocol, message, original,
            addr=None, state=None, version=None, completed_pages=None,
            total_pages=None, t=None, pdu=None):
    return _LogLine(timestamp=timestamp, log_level=log_level,
                    protocol=protocol, message=message, original=original,
                    addr=addr, state=state, version=version,
                    completed_pages=completed_pages, total_pages=total_pages,
                    t=t, pdu=pdu)


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
    if msg_matches is not None:
        msg_groups = msg_matches.groups()
        addr = int(msg_groups[0])
        state = msg_groups[1]
        version = int(msg_groups[2])
        completed_pages = int(msg_groups[3])
        total_pages = int(msg_groups[4])
        t = float(msg_groups[5])
        pdu = msg_groups[6]
        return LogLine(timestamp=timestamp, log_level=log_level,
                       protocol=protocol, message=message, original=line,
                       addr=addr, state=state, version=version,
                       completed_pages=completed_pages, total_pages=total_pages,
                       t=t, pdu=pdu)
    else:
        return LogLine(timestamp=timestamp, log_level=log_level, original=line,
                       protocol=protocol, message=message)
