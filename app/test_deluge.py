from deluge import *
from nose.tools import eq_
from nose.tools import ok_


def test_split_data_into_pages_and_packets():
    d = Deluge()
    eq_({}, d.complete_pages)
    eq_([], d.packets_per_page)

    # Change sizes of page and packet for test.
    Deluge.PAGE_SIZE = 4
    Deluge.PACKET_SIZE = 2

    d._split_data_into_pages_and_packets("123456789")

    # Expected pages/packets
    expected_page_0 = {0: "12", 1: "34"}
    expected_page_1 = {0: "56", 1: "78"}
    expected_page_2 = {0: "9"}
    expected_pages = {
        0: expected_page_0,
        1: expected_page_1,
        2: expected_page_2,
    }

    eq_(expected_pages, d.complete_pages)
    eq_([2, 2, 1], d.packets_per_page)