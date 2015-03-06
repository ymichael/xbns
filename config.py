#
# XBee configuration.
#

# Channel ID: [11, 26]
CHANNEL = 14

# PAN ID: 64 bits
PANID = 0xdcaa

def get_addr():
    with open ("addr.txt", "r") as f:
        addr = f.readline()
    return int(addr)

# ADDR: 16 bits [0, 65536]
ADDR = get_addr()


import __main__
import os

def get_log_file_name():
    directory = os.path.dirname(os.path.realpath(__file__))
    log_directory = 'log'
    main_file = __main__.__file__
    main_file = main_file.replace('./', '')
    main_file = main_file.replace('/', '-')
    main_file = main_file.replace('.py', '')
    file_name = '%s-%s.log' % (main_file, ADDR)
    return os.path.join(*[directory, log_directory, file_name])


SHOULD_LOG = True


LOG_FILE_NAME = get_log_file_name()