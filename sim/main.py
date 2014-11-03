from network import Network
from node import Node
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

    nodes = {}
    network = Network()
    for addr, outgoing_links in topo:
        node = Node.create(addr)
        network.add_node(node, outgoing_links)
        nodes[addr] = node

    # Start the network.
    network.start()

    # Don't terminate.
    while True:
        nodes[1].send("hello world", 11)
        time.sleep(5)
