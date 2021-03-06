import re

# A network topology is represented as:
# [ (<addr>, <set of addrs that node links to>), ...]
# eg.
#     [1] <=> [2] <=> [3] <=> [4] <=> [5]
#
#     [
#     	(1, {2}),
#     	(2, {1, 3}),
#     	(3, {2, 4}),
#     	(4, {3, 5}),
#     	(5, {4}),
#     ]
def all_nodes(topo):
    return {x[0] for x in topo}


def largest_addr(topo):
    return max(all_nodes(topo))


def smallest_addr(topo):
    return min(all_nodes(topo))


def merge_topologies(topo1, topo2):
    assert len(all_nodes(topo1).intersection(all_nodes(topo2))) == 0
    retval = []
    retval.extend(topo1)
    retval.extend(topo2)
    return retval


def topo_to_dict(topo):
    return {t[0]: t[1] for t in topo}


def dict_to_topo(topo_dict):
    return [(k, v) for k, v in topo_dict.iteritems()]


def add_link(topo, a, b):
    """Adds a link from `a` to `b`.

    `a` and `b` can be iterable.
    """
    try:
        iter(a)
        iter_a = a
    except TypeError, te:
        iter_a = [a]
    try:
        iter(b)
        iter_b = b
    except TypeError, te:
        iter_b = [b]


    topo_dict = topo_to_dict(topo)
    for a in iter_a:
        for b in iter_b:
            if a == b:
                continue
            topo_dict[a].add(b)
            topo_dict[b].add(a)
    return dict_to_topo(topo_dict)


def clique(size, start_addr=0):
    """Returns a clique of the given size."""
    nodes = []
    for i in xrange(size):
        addr = i + start_addr
        nodes.append(addr)

    topology = []
    for node in nodes:
        links = set(nodes)
        links.remove(node)
        topology.append((node, links))
    return topology


def _addr_generator(start_addr):
    """Helper to return a function that return the next addr to use."""
    hack = [start_addr]
    def next_addr():
        retval = hack[0]
        hack[0] += 1
        return retval
    return next_addr


def nary_tree(height, n, start_addr=0):
    """Returns a n-ary tree of height n."""
    assert height >= 0
    get_next_addr = _addr_generator(start_addr)
    topology = []
    to_process = [(get_next_addr(), set(), 0)]
    while len(to_process) != 0:
        current, links, depth = to_process.pop()
        if depth < height:
            children = [get_next_addr() for i in xrange(n)]
            links.update(children)
            for child in reversed(children):
                to_process.append((child, {current}, depth + 1))
        topology.append((current, links))
    return topology


def chain(length, start_addr=0):
    """Returns a network with n nodes connected in a chain."""
    return nary_tree(length - 1, 1, start_addr=start_addr)

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

COMPONENT_REGEXP = '([lc])\[(\d*)\,?\s?(\d*)?\]'

COMPONENTS_FUNC = {
    'l': chain,
    'c': clique,
}


def parse_topology(topo):
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
                start_addr = largest_addr(components[-1]) + 1
        else:
            start_addr = int(start_addr)
        components.append(
            COMPONENTS_FUNC[component_type](int(number), start_addr))

    # Merge components and add links.
    while len(components) != 1:
        last = components.pop()
        second_last = components.pop()
        merged = merge_topologies(last, second_last)
        merged = add_link(merged, largest_addr(second_last), smallest_addr(last))
        components.append(merged)

    # Add additional edges specified.
    merged_topology = components[0]

    if edges != '':
        for edge in edges.split(','):
            a, b = edge.split('-')
            merged_topology = add_link(merged_topology, int(a), int(b))

    return merged_topology
