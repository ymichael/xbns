.PHONY: start port rsync rmpyc rsync-makefile sim test

rmpyc:
	find . | grep -v .venv | grep .pyc | xargs rm


# XBee network configuration. Change as necessary.
MYID := 0x1222
CHANNEL := 0x13
PANID := 0xabdd

# Find out which serial port to use
# Matches /dev/tty.usbserial && /dev/ttyUSB0
SERIALPORT = $(shell find /dev | egrep -i "ttyUSB|tty.*usbserial")

port:
	echo $(SERIALPORT)


start:
	PYTHONPATH=. python net/stack.py \
		--panid=$(PANID) \
		--channel=$(CHANNEL) \
		--myid=$(MYID) \
		--port=$(SERIALPORT)

sim:
	PYTHONPATH=. python sim/main.py $(ARGS)

test:
	PYTHONPATH=. nosetests

# rsync repository with beaglebone (w/o makefile)
rsync:
	rsync -avz \
		--exclude=.git \
		--exclude=.venv \
		--exclude=*.pyc \
		--exclude=Makefile \
		. michael@bone:~/xbns

rsync-xbee:
	rsync -avz .venv/lib/python2.7/site-packages/xbee michael@bone:~/xbns

# rsync makefile.
rsync-makefile:
	rsync Makefile michael@bone:~/xbns/Makefile
