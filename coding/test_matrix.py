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
    m3 = m1.dot(m2)
    eq_(m2, m3)


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

    mc = ma.dot(mb)
    eq_(m_expected, mc)


def test_swap_rows():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [7, 8, 9],
        [4, 5, 6],
        [1, 2, 3],
    ]
    mb = Matrix(b)
    mb.swap_rows(0, 2)
    eq_(Matrix(expected), mb)


def test_mul():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [3, 6, 9],
        [12, 15, 18],
        [21, 24, 27],
    ]
    mb = Matrix(b)
    mb.mul(3)
    eq_(Matrix(expected), mb)


def test_mul_row():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [3, 6, 9],
        [4, 5, 6],
        [7, 8, 9],
    ]
    mb = Matrix(b)
    mb.mul_row(0, 3)
    eq_(Matrix(expected), mb)

def test_remove_row():
    b = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [1, 2, 3],
        [7, 8, 9],
    ]
    mb = Matrix(b)
    mb.remove_row(1)
    eq_(Matrix(expected), mb)
