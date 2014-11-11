from nose.tools import eq_
from nose.tools import ok_
from gaussian import *


def test_gaussian_elimination_solve_1():
    # 2x + y = 5
    # y = 1
    g = GaussianElimination()
    g.add_row([2, 1], [5])
    g.add_row([0, 1], [1])
    eq_(0, g.get_rows_required())
    ok_(g.is_solved())
    eq_([[2], [1]], g.solve())


def test_gaussian_elimination_solve_2():
    # 2x + y - 3z = -4
    # x + y + 3z = 17
    # x - 2y + z = 3
    g = GaussianElimination()
    g.add_row([2, 1, -3], [-4])
    g.add_row([1, 1, 3], [17])
    g.add_row([1, -2, 1], [3])
    eq_([[3], [2], [4]], g.solve())
    eq_(0, g.get_rows_required())
    ok_(g.is_solved())


def test_gaussian_elimination_non_innovative():
    # 2x + y - 3z = -4
    # x + y + 3z = 17
    # x - 2y + z = 3
    g = GaussianElimination()
    g.add_row([2, 1, -3], [-4])
    eq_(2, g.get_rows_required())
    ok_(not g.is_solved())

    g.add_row([4, 2, -6], [-8])
    eq_(2, g.get_rows_required())
    ok_(not g.is_solved())


def test_gaussian_elimination_rows_required():
    # 2x + y - 3z = -4
    # x + y + 3z = 17
    # x - 2y + z = 3
    g = GaussianElimination()
    g.add_row([2, 1, -3], [-4])
    eq_(2, g.get_rows_required())
    g.add_row([1, 1, 3], [17])
    eq_(1, g.get_rows_required())
    g.add_row([1, -2, 1], [3])
    eq_(0, g.get_rows_required())
    eq_([[3], [2], [4]], g.solve())
    ok_(g.is_solved())

