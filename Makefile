.PHONY: start port rsync

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
	python main.py \
		--panid=$(PANID) \
		--channel=$(CHANNEL) \
		--myid=$(MYID) \
		--port=$(SERIALPORT)

rsync:
	rsync -avz --exclude=.venv --exclude=*.pyc --exclude=Makefile . michael@bone:~/xbns
