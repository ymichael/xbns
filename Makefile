.PHONY: start port rsync rmpyc rsync-makefile sim test app pong ping

rmpyc:
	find . | grep -v .venv | grep .pyc | xargs rm

# Find out which serial port to use
# Matches /dev/tty.usbserial && /dev/ttyUSB0
SERIALPORT = $(shell find /dev | egrep -i "ttyUSB|tty.*usbserial")

port:
	echo $(SERIALPORT)

start:
	PYTHONPATH=. python net/main.py --port=$(SERIALPORT)

app:
	PYTHONPATH=. python net/layers/application.py

pong:
	PYTHONPATH=. python app/pong.py

ping:
	PYTHONPATH=. python app/ping.py

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
