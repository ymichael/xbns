from nose.tools import eq_
from nose.tools import ok_
from matrix import *


def test_create_matrix():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    ma = Matrix()
    mb = Matrix(b)
    eq_(b, mb.rows)
    eq_([], ma.rows)


def test_create_invalid_matrix():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9, 10],
    ]
    try:
        mb = Matrix(b)
        ok_(False)
    except InvalidMatrixException:
        # Expected
        pass


def test_matrix_properties():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    mb = Matrix(b)
    eq_(3, mb.num_rows)
    eq_(3, mb.num_cols)

    ma = Matrix()
    eq_(0, ma.num_rows)
    eq_(None, ma.num_cols)


def test_add_row():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    ma = Matrix()
    mb = Matrix(b)
    for row in b:
        ma.add_row(row)
    eq_(ma, mb)

    eq_(3, ma.num_rows)
    eq_(3, ma.num_cols)
    ma.add_row([10, 11, 12])
    eq_(4, ma.num_rows)
    eq_(3, ma.num_cols)


def test_add_invalid_row():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    mb = Matrix(b)
    try:
        mb.add_row([10, 11, 12, 13])
        ok_(False)
    except InvalidRowSizeException:
        # Expected
        pass


def test_dot_product_identity():
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

    m1 = Matrix(i3)
    m2 = Matrix(b)
    m1.dot(m2)
    eq_(m1, m2)


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

    ma = Matrix(a)
    mb = Matrix(b)
    m_expected = Matrix(expected)

    ma.dot(mb)
    eq_(m_expected, ma)
