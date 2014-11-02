from network import Network
from radio import Radio
import net.stack
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
        # Create radio for each node and register radio with the network.
        radio = Radio(addr)
        network.add_radio(radio, outgoing_links)
        # Create stack for each node.
        stack = net.stack.Stack.create(addr, radio)
        network.add_node(stack)
        nodes[addr] = stack

    # Start the network.
    network.start()

    # Don't terminate.
    while True:
        nodes[1].send("hello world", 11)
        time.sleep(5)
