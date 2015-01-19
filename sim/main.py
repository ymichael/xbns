from network import Network
from node import Node
import time
import topology

# Applications
import app.basic
import app.flooding
import app.deluge2


def file_contents(filepath):
    f = open(filepath, 'r')
    retval = f.read()
    f.close()
    return retval


if __name__ == '__main__':
    # Create a 15 node network:
    # chain <=> clique <=> chain
    chain = topology.chain(2, start_addr=1)
    chain2 = topology.chain(2, start_addr=10)
    clique = topology.clique(3, start_addr=20)
    topo = topology.merge_topologies(chain, clique)
    topo = topology.add_link(topo, 2, 20)
    topo = topology.merge_topologies(topo, chain2)
    topo = topology.add_link(topo, 22, 10)

    # Set up nodes in the network.
    nodes = {}
    network = Network(delay=0)
    for addr, outgoing_links in topo:
        node = Node.create(addr)
        nodes[addr] = node
        network.add_node(node, outgoing_links)
    # Start the network.
    network.start()

    # Add applications to run on each node.
    # port_num = 100
    # for addr, node in nodes.iteritems():
    #     node.add_app(app.basic.Basic(port_num))

    for addr, node in nodes.iteritems():
        node.add_app(app.deluge2.Deluge())
    

    # Data
    data = file_contents("./data/2.in")

    nodes[1].get_app(app.deluge2.Deluge.PORT) \
        .new_version(1, data)
    # Don't terminate.
    time.sleep(500)
