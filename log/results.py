import argparse
import utils

def to_csv(values):
    return ", ".join(str(v) for v in values)

class Mode(object):
    STATS = 'stats'
    SCATTER = 'scatter'
    CHECK = 'check'
    FULL = 'full'

def check_mode(args):
    for f in args.files:
        lines = utils.get_log_lines([f])
        lines = utils.sync_timings(lines)
        nodes = utils.get_nodes(lines)
        version = utils.get_version(lines)
        t_min = utils.get_t_min(lines)
        total_pages = utils.get_total_pages(lines, version)
        start_times = utils.get_start_times(lines, nodes, t_min)
        completion_times = utils.get_completion_times(lines, nodes, total_pages, version)
        final_times = utils.get_final_times(lines, nodes, total_pages, version)
        time_taken = utils.get_time_taken(nodes, start_times, final_times)
        packets_sent = utils.get_packets_sent(lines, nodes, start_times, final_times)

        # utils.get_stats(lines)
        all_nodes_completed = time_taken.values() and min(time_taken.values()).total_seconds() == 0
        all_nodes_exists = nodes == set([2,3,4,5,6,7,8,9,10,11,20])
        if not all_nodes_completed:
            print "Not all nodes completed:", f.name
        elif not all_nodes_exists:
            print "Not all nodes exist:", f.name, nodes

def stats_mode(args):
    first_completed = []
    time_to_completion = []
    num_packets_sent = []
    num_adv_sent = []
    num_req_sent = []
    num_data_sent = []

    for f in args.files:
        lines = utils.get_log_lines([f])
        lines = utils.sync_timings(lines)
        nodes = utils.get_nodes(lines)
        version = utils.get_version(lines)
        t_min = utils.get_t_min(lines)
        total_pages = utils.get_total_pages(lines, version)
        start_times = utils.get_start_times(lines, nodes, t_min)
        completion_times = utils.get_completion_times(lines, nodes, total_pages, version)
        final_times = utils.get_final_times(lines, nodes, total_pages, version)
        time_taken = utils.get_time_taken(nodes, start_times, final_times)
        packets_sent = utils.get_packets_sent(lines, nodes, start_times, final_times)

        num_adv_sent.append(sum(v[0] for v in packets_sent.values()))
        num_req_sent.append(sum(v[1] for v in packets_sent.values()))
        num_data_sent.append(sum(v[2] for v in packets_sent.values()))
        num_packets_sent.append(sum(sum(v) for v in packets_sent.values()))
        time_to_completion.append(max(time_taken.values()).total_seconds())
        first_completed.append(min(v.total_seconds() for v in time_taken.values() if v.total_seconds()))
    avg_time_to_completion = sum(time_to_completion) / len(time_to_completion)
    print "Average Time to Completion:", avg_time_to_completion
    avg_first_completed = sum(first_completed) / len(first_completed)
    print "Average Time for first node:", avg_first_completed
    print "Average Delta:", avg_time_to_completion - avg_first_completed

    avg_packets_sent = float(sum(num_packets_sent)) / len(num_packets_sent)
    avg_adv_sent = sum(num_adv_sent) / len(num_adv_sent)
    avg_req_sent = sum(num_req_sent) / len(num_req_sent)
    avg_data_sent = sum(num_data_sent) / len(num_data_sent)

    print "Average Packets Sent:", avg_packets_sent
    print "Total ADV Sent:", avg_adv_sent
    print "Total REQ Sent:", avg_req_sent
    print "Total DATA Sent:", avg_data_sent

    print "Average ADV Sent %:", 100 * avg_adv_sent / avg_packets_sent
    print "Average REQ Sent %:", 100 * avg_req_sent / avg_packets_sent
    print "Average DATA Sent %:", 100 * avg_data_sent / avg_packets_sent


def scatter_mode(args):
    for f in args.files:
        lines = utils.get_log_lines([f])
        lines = utils.sync_timings(lines)
        nodes = utils.get_nodes(lines)
        version = utils.get_version(lines)
        t_min = utils.get_t_min(lines)
        total_pages = utils.get_total_pages(lines, version)
        start_times = utils.get_start_times(lines, nodes, t_min)
        completion_times = utils.get_completion_times(lines, nodes, total_pages, version)
        final_times = utils.get_final_times(lines, nodes, total_pages, version)
        time_taken = utils.get_time_taken(nodes, start_times, final_times)
        packets_sent = utils.get_packets_sent(lines, nodes, start_times, final_times)


        all_nodes_completed = time_taken.values() and min(time_taken.values()).total_seconds() == 0
        all_nodes_exists = nodes == set([2,3,4,5,6,7,8,9,10,11,20])
        if not all_nodes_completed:
            continue
        # elif not all_nodes_exists:
        #     continue
        elif len(nodes) < 7:
            continue

        if args.l:
            for n in nodes:
                if not time_taken.get(n) or time_taken[n].total_seconds() == 0 or packets_sent[n][2] < 100:
                    continue
                print time_taken[n].total_seconds(), 100 * float(packets_sent[n][0] + packets_sent[n][1]) / sum(packets_sent[n]), 1
        else:
            adv_sent = sum(v[0] for v in packets_sent.values())
            req_sent = sum(v[1] for v in packets_sent.values())
            data_sent = sum(v[2] for v in packets_sent.values())
            total_sent = sum(sum(v) for v in packets_sent.values())        
            completion_time = max(time_taken.values()).total_seconds()
            print completion_time, 100 * float(adv_sent + req_sent) / total_sent, 1


def main(args):
    if args.mode == Mode.STATS:
        return stats_mode(args)
    if args.mode == Mode.CHECK:
        return check_mode(args)
    if args.mode == Mode.SCATTER:
        return scatter_mode(args)
    if args.mode == Mode.FULL:
        for f in args.files:
            lines = utils.get_log_lines([f])
            utils.get_stats(lines)
        return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Results Logfile Parser')
    parser.add_argument('files', metavar='LOGFILE', nargs='+',
                        type=argparse.FileType('r'), help="Logfiles of runs to parse.")
    parser.add_argument('--mode', '-m', type=str, default=Mode.CHECK,
                        choices=[Mode.STATS, Mode.CHECK, Mode.FULL, Mode.SCATTER])
    parser.add_argument('-l', action='store_true')
    args = parser.parse_args()
    main(args)