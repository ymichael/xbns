from network import Network
from node import Node
import app.basic
import time
import topology


if __name__ == '__main__':
    # Create a 15 node network:
    # chain <=> clique <=> chain
    chain = topology.chain(5, start_addr=1)
    chain2 = topology.chain(5, start_addr=10)
    clique = topology.clique(5, start_addr=20)
    topo = topology.merge_topologies(chain, clique)
    topo = topology.add_link(topo, 1, 20)
    topo = topology.merge_topologies(topo, chain2)
    topo = topology.add_link(topo, 22, 10)

    # Set up nodes in the network.
    nodes = {}
    network = Network()
    for addr, outgoing_links in topo:
        node = Node.create(addr)
        nodes[addr] = node
        network.add_node(node, outgoing_links)
    # Start the network.
    network.start()

    # Add applications to run on each node.
    port_num = 100
    for addr, node in nodes.iteritems():
        node.add_app(app.basic.Basic(port_num))

    # Don't terminate.
    while True:
        nodes[1].get_app(port_num).send("hello world", 11)
        time.sleep(5)
