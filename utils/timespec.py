import cli
import ctypes
import ctypes.util
import datetime
import time


class TimeSpec(ctypes.Structure):
    # Source: http://stackoverflow.com/a/12292874/1070617
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

    @staticmethod
    def set_time_zone():
        # TODO: Get global logger for easier debugging when something goes wrong
        # in the nodes.
        cli.call(["unlink", "/etc/localtime"])
        cli.call(["ln", "-s", "/usr/share/zoneinfo/Singapore", "/etc/localtime"])

    @staticmethod
    def get_current_time(delta=None):
        current_time = datetime.datetime.now()
        if delta is not None:
            current_time += delta
        current_milliseconds = current_time.microsecond / 1000
        time_tuple = current_time.timetuple()[:6] + (current_milliseconds,)
        return time_tuple

    @staticmethod
    def set_time(time_tuple):
        TimeSpec.set_time_zone()
        try:
            librt = ctypes.CDLL(ctypes.util.find_library("rt"))
            ts = TimeSpec()
            ts.tv_sec = int(time.mktime(datetime.datetime(*time_tuple[:6]).timetuple()))
            ts.tv_nsec = time_tuple[6] * 1000000
            librt.clock_settime(0, ctypes.byref(ts))
        except Exception, e:
            print str(e)
