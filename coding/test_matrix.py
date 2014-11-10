from nose.tools import eq_
from nose.tools import ok_
from matrix import *


def test_assert_rows_and_cols():
    matrix = [
        [1, 2, 3],
        [1, 2, 3],
        [1, 2, 3],
    ]
    assert_rows(matrix, 3)
    assert_cols(matrix, 3)


def test_assert_rows_and_cols_fail():
    matrix = [
        [1, 2, 3],
        [1, 2, 3],
        [1, 2, 3, 4],
    ]
    try:
        assert_cols(matrix, 3)
        ok_(False)
    except AssertionError, expected:
        pass


def test_dot_product_identiry():
    i3 = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
    ]
    b = [
        [1, 2, 3],
        [1, 2, 3],
        [1, 2, 3],
    ]
    eq_(b, dot(i3, b))


def test_dot_product_unequal():
    a = [
        [1, 2],
        [3, 4],
    ]
    b = [
        [5, 6, 7],
        [8, 9, 10],
    ]
    expected = [
        [21, 24, 27],
        [47, 54, 61],
    ]
    eq_(expected, dot(a, b))
