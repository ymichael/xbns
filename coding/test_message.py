from nose.tools import eq_
from nose.tools import ok_
from message import *


def test_round_trip_long():
    data = "This is a string blah blah blah."
    rows = 5
    m = Message(data)
    m_sized = m.to_size(100)
    eq_(100, len(m_sized))

    m2 = Message.from_string(m_sized)
    eq_(data, m2.string)

def test_round_trip_short():
    data = "This is a string blah blah blah."
    rows = 5
    m = Message(data)
    m_sized = m.to_size(len(data))
    eq_(32, len(m_sized))

    m2 = Message.from_string(m_sized)
    eq_(data, m2.string)


def test_escape_single():
    eq_([219, 220], Message.escape([192]))
    eq_([219, 221], Message.escape([219]))
    eq_([123, 219, 220, 123], Message.escape([123, 192, 123]))
    eq_([123, 219, 221, 123], Message.escape([123, 219, 123]))


def test_escape_multiple():
    eq_([219, 220, 219, 220], Message.escape([192, 192]))
    eq_([219, 221, 219, 221], Message.escape([219, 219]))
    eq_([219, 220, 219, 221], Message.escape([192, 219]))

    eq_([1, 219, 220, 2, 219, 220, 3], Message.escape([1, 192, 2, 192, 3]))
    eq_([4, 219, 221, 5, 219, 221, 6], Message.escape([4, 219, 5, 219, 6]))
    eq_([7, 219, 220, 8, 219, 221, 9], Message.escape([7, 192, 8, 219, 9]))


def test_unescape_single():
    eq_([1, 192, 2], Message.unescape([1, 219, 220, 2]))
    eq_([1, 219, 2], Message.unescape([1, 219, 221, 2]))


def test_unescape_multiple():
    eq_([1, 192, 2, 192, 3], Message.unescape([1, 219, 220, 2, 219, 220, 3]))
    eq_([1, 219, 2, 219, 3], Message.unescape([1, 219, 221, 2, 219, 221, 3]))
    eq_([1, 219, 2, 192, 3], Message.unescape([1, 219, 221, 2, 219, 220, 3]))
