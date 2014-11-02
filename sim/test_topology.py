from nose.tools import eq_
from nose.tools import ok_
from topology import *


def test_clique_1():
    expected = [(0, set())]
    eq_(expected, clique(1))


def test_clique_2():
    expected = [
        (1, {2}),
        (2, {1}),
    ]
    eq_(expected, clique(2, start_addr=1))


def test_clique_many():
    expected = [
        (1, {2, 3, 4, 5}),
        (2, {1, 3, 4, 5}),
        (3, {1, 2, 4, 5}),
        (4, {1, 2, 3, 5}),
        (5, {1, 2, 3, 4}),
    ]
    eq_(expected, clique(5, start_addr=1))


def test_nary_1():
    expected = [(0, set())]
    eq_(expected, nary_tree(0, 2))


def test_nary_2_3():
    expected = [
        (0, {1, 2, 3}),
        (1, {0, 4, 5, 6}),
        (4, {1}), (5, {1}), (6, {1}),
        (2, {0, 7, 8, 9}),
        (7, {2}), (8, {2}), (9, {2}),
        (3, {0, 10, 11, 12}),
        (10, {3}), (11, {3}), (12, {3}),
    ]
    eq_(sorted(expected), sorted(nary_tree(2, 3)))


def test_nary_2_2():
    expected = [
        (1, {2, 3}),
        (2, {1, 4, 5}),
        (4, {2}), (5, {2}),
        (3, {1, 6, 7}),
        (6, {3}), (7, {3}),
    ]
    eq_(sorted(expected), sorted(nary_tree(2, 2, start_addr=1)))


def test_chain():
    expected = [
        (1, {2}), (2, {1, 3}), (3, {2, 4}),
        (4, {3, 5}), (5, {4}),
    ]
    eq_(sorted(expected), sorted(chain(5, start_addr=1)))


def test_all_nodes():
    topo = [
        (1, {2, 3}),
        (2, {1, 4, 5}),
        (4, {2}), (5, {2}),
        (3, {1, 6, 7}),
        (6, {3}), (7, {3}),
    ]
    eq_(sorted({1, 2, 3, 4, 5, 6, 7}), sorted(all_nodes(topo)))


def test_largest_addr():
    topo = [
        (1, {2, 3}),
        (2, {1, 4, 5}),
        (3, {1, 6, 7}),
        (4, {2}),
        (5, {2}),
        (6, {3}),
        (7, {3}),
    ]
    eq_(7, largest_addr(topo))


def test_merge_topologies():
    topo1 = [(1, {2, 3}), (2, {1}), (3, {1})]
    topo2 = [(4, {5, 6}), (5, {4}), (6, {4})]
    expected = [
        (1, {2, 3}), (2, {1}), (3, {1}),
        (4, {5, 6}), (5, {4}), (6, {4}),
    ]
    eq_(sorted(expected), sorted(merge_topologies(topo1, topo2)))


def test_topo_to_dict_round_trip():
    topo1 = [(1, {2, 3}), (2, {1}), (3, {1})]
    topo2 = [(4, {5, 6}), (5, {4}), (6, {4})]
    eq_(sorted(topo1), sorted(dict_to_topo(topo_to_dict(topo1))))
    eq_(sorted(topo2), sorted(dict_to_topo(topo_to_dict(topo2))))


def test_add_link_all():
    chain_topo = chain(5)
    clique_topo = clique(5)
    nodes = all_nodes(chain_topo)
    new_topo = add_link(chain_topo, nodes, nodes)
    eq_(clique_topo, chain_topo)


def test_add_link_in_parts():
    chain_topo = chain(3)
    clique_topo = clique(3)
    new_topo = add_link(chain_topo, 0, 2)
    new_topo = add_link(chain_topo, 2, 0)
    eq_(clique_topo, chain_topo)


def test_add_link_iterable():
    chain_topo = chain(4)
    clique_topo = clique(4)
    new_topo = add_link(chain_topo, 0, [2, 3])
    new_topo = add_link(chain_topo, 1, [3])
    new_topo = add_link(chain_topo, 2, [0])
    new_topo = add_link(chain_topo, 3, [0, 1])
    eq_(clique_topo, chain_topo)
