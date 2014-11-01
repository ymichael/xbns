from network import Network
import fake.radio
import net.stack
import time


if __name__ == '__main__':
	# Simple multi-hop topology.
	# [1] <=> [2] <=> [3] <=> [4] <=> [5]
	topology = [
		(1, [2]),
		(2, [1, 3]),
		(3, [2, 4]),
		(4, [3, 5]),
		(5, [4]),
	]
	nodes = []
	network = Network()
	for addr, outgoing_links in topology:
		# Create radio for each node and register radio with the network.
		radio = fake.radio.FakeRadio(addr)
		network.add_radio(radio, outgoing_links)
		# Create stack for each node.
		stack = net.stack.Stack.create(addr, radio)
		nodes.append(stack)

	# Start the network and all nodes.
	network.start()
	for node in nodes:
		node.start()

	# Don't terminate.
	while True:
		# for node in nodes:
		# 	node.send(str(node.addr) * 1000)
		nodes[0].send("hello world", 5)
		time.sleep(5)