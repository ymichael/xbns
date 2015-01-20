from network import Network
from node import Node
from pprint import pprint

import argparse
import time
import topology

import app.deluge
import app.flooding
import app.rateless_deluge


# The various protocols that can be used in the simulator.
PROTOCOLS = {
    'flooding': app.flooding.Flooding,
    'deluge': app.deluge.Deluge,
    'rateless': app.rateless_deluge.RatelessDeluge,
}


def main(args):
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
        node.add_app(APP_CLS())

    # Read file and seed in the network.
    data = args.file.read()
    args.file.close()
    for addr in args.seed:
        nodes[addr].get_app(APP_CLS.PORT).new_version(1, data)

    # Don't terminate.
    time.sleep(500)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='XBNS Simulator', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--protocol', '-p', required=True,
                        choices=PROTOCOLS.keys(),
                        help='Protocol to run in simulation.')
    # TODO: A easy way to specify topology.
    parser.add_argument('--topo', '-t', default='l[2, 1]-c[3, 10]-l[2, 20]',
                        help=topology.TOPOLOGY_HELP)
    parser.add_argument('--seed', '-s', nargs='*', type=int, default=[1],
                        help='Node IDs to seed the file initially, defaults to 1')
    parser.add_argument('--loss', '-l', default=0, type=int,
                        help='The packet loss rate, defaults to 0.')
    parser.add_argument('--delay', '-d', default=0, type=int,
                        help='The propogation delay in the shared medium, defaults to 0.')
    parser.add_argument('--file', '-f', type=argparse.FileType(),
                        default='./data/2.in',
                        help='File to propogate through the network')
    args = parser.parse_args()
    main(args)
