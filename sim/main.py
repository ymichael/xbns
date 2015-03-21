from network import Network
from node import Node
from pprint import pprint

import app.deluge
import app.pong
import app.protocol.rateless_deluge
import app.rateless_deluge
import argparse
import config
import time
import topology


# The various protocols that can be used in the simulator.
PROTOCOLS = {
    'deluge': app.deluge.Deluge,
    'rateless': app.rateless_deluge.RatelessDeluge,
    'pong': app.pong.Pong,
    'toporeq': app.pong.Pong,
    'topoflood': app.pong.Pong,
    'make': app.pong.Pong,
}


def main(args):
    config.SHOULD_LOG = args.log
    topo = topology.parse_topology(args.topo)

    print "\n"
    print "########################################"
    print "#        SIMULATION PARAMETERS.        #"
    print "########################################"
    pprint(args.__dict__)
    print "\n"
    print "########################################"
    print "#              TOPOLOGY.               #"
    print "########################################"
    pprint(topo)
    print "\n"
    print "########################################"
    print "#            SIMULATION LOG.           #"
    print "########################################"

    # Set up nodes in the network.
    nodes = {}
    network = Network(delay=args.delay, loss=args.loss)
    for addr, outgoing_links in topo:
        node = Node.create(addr)
        nodes[addr] = node
        network.add_node(node, outgoing_links)

    # Start the network.
    network.start()

    # Run protocol.
    APP_CLS = PROTOCOLS[args.protocol]
    for addr, node in nodes.iteritems():
        node.start_application(APP_CLS(addr))

    if args.protocol == 'pong':
        for addr in args.seed:
            nodes[addr].get_application(APP_CLS.ADDRESS).send_ping()
            nodes[addr].get_application(APP_CLS.ADDRESS).send_time_set()

    if args.protocol == 'make':
        assert args.target
        for addr in args.seed:
            nodes[addr].get_application(APP_CLS.ADDRESS).set_mode(app.pong.Mode.MAKE)
            nodes[addr].get_application(APP_CLS.ADDRESS).send_make_flood(args.target)

    if args.protocol == 'toporeq':
        for addr in args.seed:
            nodes[addr].get_application(APP_CLS.ADDRESS).send_topo_req()

    if args.protocol == 'topoflood':
        for addr in args.seed:
            nodes[addr].get_application(APP_CLS.ADDRESS).send_topo_flood()

    if args.protocol == 'deluge' or args.protocol == 'rateless':
        for addr, node in nodes.iteritems():
            application = node.get_application(APP_CLS.ADDRESS)
            application.stop_protocol()
            application.protocol.K = args.k
            application.protocol.T_MIN = args.tmin
            application.protocol.T_MAX = args.tmax
            application.protocol.FRAME_DELAY = args.framedelay
            application.protocol.T_R = args.t_r
            application.protocol.T_TX = args.t_tx
            application.protocol.W = args.w
            application.protocol.RX_MAX = args.rx_max
            if args.protocol == 'deluge':
                assert args.dpagesize % args.dpacketsize == 0
                application.protocol.PAGE_SIZE = args.dpagesize
                application.protocol.PACKET_SIZE = args.dpacketsize
                application.protocol.PACKETS_PER_PAGE = args.dpagesize / args.dpacketsize
            elif args.protocol == 'rateless':
                assert args.rpagesize % args.rpacketsize == 0
                application.protocol.PAGE_SIZE = args.rpagesize
                application.protocol.PACKET_SIZE = args.rpacketsize
                application.protocol.PACKETS_PER_PAGE = args.rpagesize / args.rpacketsize
                application.protocol.PDU_CLS.DATA_FORMAT = "II" + ("B" * application.protocol.PACKETS_PER_PAGE) + \
                    ("B" * application.protocol.PACKET_SIZE)
                # TODO: Cleaner way to do this.
                app.protocol.rateless_deluge.ROWS_REQUIRED = args.rpagesize / args.rpacketsize
            application.start_protocol()

        # Read file and seed in the network.
        data = args.file.read()
        args.file.close()
        for addr in args.seed:
            nodes[addr].get_application(APP_CLS.ADDRESS).disseminate(data)

    # Don't terminate.
    while True:
        time.sleep(100)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='XBNS Simulator', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--protocol', '-p', default='deluge',
                        choices=PROTOCOLS.keys(),
                        help='Protocol to run in simulation.')
    parser.add_argument('--log', type=bool, default=False,
                        help='Whether to write to log file.')

    # TODO: A easy way to specify topology.
    network = parser.add_argument_group('Network Configuration')
    network.add_argument('--topo', '-t', default='l[2, 1]-c[3, 10]-l[2, 20]',
                         help=topology.TOPOLOGY_HELP)
    network.add_argument('--seed', '-s', nargs='*', type=int, default=[1],
                         help='Node IDs to seed the file initially, defaults to 1')
    network.add_argument('--loss', '-l', default=0, type=float,
                         help='The packet loss rate, defaults to 0.')
    network.add_argument('--delay', '-d', default=0, type=float,
                         help='The propogation delay in the shared medium, defaults to 0.')

    common = parser.add_argument_group('Deluge/Rateless Common Configuration')
    common.add_argument('--file', '-f', type=argparse.FileType(),
                        default='./data/20KB.in',
                        help='File to propagate through the network')
    common.add_argument('-k', type=int, default=1,
                        help='Number of overheard messages to trigger message suppression.')
    common.add_argument('--tmin', type=float, default=1,
                        help='The lower bound for the round window length, in seconds.')
    common.add_argument('--tmax', type=float, default=60 * 10,
                        help='The upper bound for the round window length, in seconds.')
    common.add_argument('--framedelay', type=float, default=.02,
                        help='The time taken for a frame to leave the xbee after it is sent.')
    common.add_argument('--t_r', type=float, default=.5)
    common.add_argument('--t_tx', type=float, default=.2)
    common.add_argument('--w', type=int, default=10)
    common.add_argument('--rx_max', type=int, default=2)

    # Deluge page/packet size
    deluge = parser.add_argument_group('Deluge Specific Configuration')
    deluge.add_argument('--dpagesize', type=int, default=1020,
                        help='Deluge: The number of bytes in each page.')
    deluge.add_argument('--dpacketsize', type=int, default=60,
                        help='Deluge: The number of bytes in each packet.')

    # Rateless page/packet size
    rateless = parser.add_argument_group('Rateless Specific Configuration')
    rateless.add_argument('--rpagesize', type=int, default=900,
                          help='Rateless: The number of bytes in each page.')
    rateless.add_argument('--rpacketsize', type=int, default=45,
                          help='Rateless: The number of bytes in each packet.')

    # Make
    parser.add_argument('--target', type=str, default="yo", help='Makefile target.')

    args = parser.parse_args()
    main(args)
