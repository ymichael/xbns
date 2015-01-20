from network import Network
from node import Node

import argparse
import re
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

TOPOLOGY_HELP = """\
Specify the network topology of the network.
* Node IDs will be assigned from the left to right in order.
* Node IDs start from 1.
* Links are always between the last node of the left component
  and the first node of the right component.

Examples:
* l[2] => list of 2 nodes
* c[3] => clique of 2 nodes
* l[2]-c[3] => list of 2 nodes connected to a clique of 3 nodes
* l[2, 3] => list of 2 node, node id starting from 3
* c[3, 10] => clique of 2 nodes, node id starting from 10
* l[5, 1]+1-3,1-4 => list of 5 nodes, with edges between 1, 3 and 1, 4.
"""

COMPONENT_REGEXP = '([lc])\[(\d*)\,?(\d*)?\]'

COMPONENTS = {
    'l': topology.chain,
    'c': topology.clique,
}


def get_topology(topo):
    topo_parts = topo.split('+')
    edges = "" if len(topo_parts) == 1 else topo_parts[1]
    topo = topo_parts[0]

    components = []
    for component in topo.split('-'):
        matches = re.search(COMPONENT_REGEXP, component)
        component_type, number, start_addr = matches.groups()
        if not start_addr:
            if len(components) == 0:
                start_addr = 1
            else:
                start_addr = topology.largest_addr(components[-1]) + 1
        else:
            start_addr = int(start_addr)
        components.append(
            COMPONENTS[component_type](int(number), start_addr))

    # Merge components and add links.
    while len(components) != 1:
        last = components.pop()
        second_last = components.pop()
        merged = topology.merge_topologies(last, second_last)
        merged = topology.add_link(
            merged,
            topology.largest_addr(second_last),
            topology.smallest_addr(last))
        components.append(merged)

    # Add additional edges specified.
    merged_topology = components[0]

    if edges != '':
        for edge in edges.split(','):
            a, b = edge.split('-')
            merged_topology = topology.add_link(
                merged_topology, int(a), int(b))

    return merged_topology


def main(args):
    # TODO: Print out a summary of the simulation being run.
    topology = get_topology(args.topo)

    # Set up nodes in the network.
    nodes = {}
    network = Network(delay=args.delay, loss=args.loss)
    for addr, outgoing_links in topology:
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
    parser.add_argument('--topo', '-t', default='l[2]-c[3]-l[2]', help=TOPOLOGY_HELP)
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
