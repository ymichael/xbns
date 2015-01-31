#
# XBee configuration.
#

# Channel ID: [11, 26]
CHANNEL = 12

# PAN ID: 64 bits
PANID = 0xabdd

def get_addr():
    with open ("addr.txt", "r") as f:
        addr = f.readline()
    return int(addr)

# ADDR: 16 bits [0, 65536]
ADDR = get_addr()
