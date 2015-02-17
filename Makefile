.PHONY: start port rsync rmpyc rsync-makefile sim test app pong ping deluge rateless settime

rmpyc:
	find . | grep -v .venv | grep .pyc | xargs rm

# Find out which serial port to use
# Matches /dev/tty.usbserial && /dev/ttyUSB0
SERIALPORT = $(shell find /dev | egrep -i "ttyUSB|tty.*usbserial")

port:
	echo $(SERIALPORT)

start:
	PYTHONPATH=. python net/main.py --port=$(SERIALPORT)

receive:
	PYTHONPATH=. python test/receive.py --port=$(SERIALPORT)

sender:
	PYTHONPATH=. python test/sender.py --port=$(SERIALPORT)

app:
	PYTHONPATH=. python net/layers/application.py

pong:
	PYTHONPATH=. python app/pong.py

ping:
	PYTHONPATH=. python app/pong.py -m ping

settime:
	PYTHONPATH=. python app/pong.py -m time

deluge:
	PYTHONPATH=. python app/run_deluge.py -f data/32B.in

manager:
	PYTHONPATH=. python app/manager.py -f data/20KB.in $(ARGS)

rateless:
	PYTHONPATH=. python app/run_rateless_deluge.py -f data/100KB.in

sim:
	PYTHONPATH=. python sim/main.py $(ARGS)

test:
	PYTHONPATH=. nosetests

# rsync repository with beaglebone (w/o makefile)
rsync:
	rsync -avz \
		--exclude=.git \
		--exclude=addr.txt \
		--exclude=.venv \
		--exclude=*.pyc \
		--exclude=out \
		. michael@bone:~/xbns
