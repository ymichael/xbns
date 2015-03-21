import argparse
import subprocess
import time
import utils



def main(args):
    """Simple script to alert when all nodes are completed."""
    # Go to the end of the file.
    f = args.f
    f.seek(0, 2)
    while True:
        where = f.tell()
        line = f.readline()
        if not line:
            time.sleep(1)
            f.seek(where)
        else:
            log_line = utils.parse_log_line(line.strip())
            if log_line is None or log_line.pdu_repr is None:
                continue
            if "ADV" in log_line.pdu_repr and str(sorted(args.nodes)) in log_line.pdu_repr:
                print log_line.original
                play_sound()


def play_sound():
    subprocess.call(["afplay", "/System/Library/Sounds/Funk.aiff"])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Logfile monitor.')
    parser.add_argument('-f', type=argparse.FileType('r'), required=True,
        help="Logfiles to monitor.")
    parser.add_argument('-n', '--nodes', type=int, metavar='NODES', nargs='+',
        help='The node ids of the nodes in the network.')
    args = parser.parse_args()
    main(args)