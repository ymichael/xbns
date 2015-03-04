.PHONY: start port rsync rmpyc rsync-makefile sim test app pong ping deluge rateless settime clearlogs setpower logs setup setaddr

setaddr:
	ssh michael@bone "echo $(ADDR) > ~/xbns/addr.txt"

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
	PYTHONPATH=. python app/pong.py --port=$(SERIALPORT)

toporeq:
	PYTHONPATH=. python app/pong.py -m toporeq --port=$(SERIALPORT)

topoflood:
	PYTHONPATH=. python app/pong.py -m topoflood --port=$(SERIALPORT)

ping:
	PYTHONPATH=. python app/pong.py -m ping --port=$(SERIALPORT)

logs:
	scp bone:~/xbns/log/* log/

settime:
	PYTHONPATH=. python app/pong.py -m time --port=$(SERIALPORT)

setpower:
	PYTHONPATH=. python app/pong.py -m power --port=$(SERIALPORT) --value=$(POWER)

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

clearlogs:
	rm log/*

setup:
	./bin/setup.sh

# rsync repository with beaglebone (w/o makefile)
rsync:
	rsync -avz \
		--exclude=.git \
		--exclude=addr.txt \
		--exclude=.venv \
		--exclude=*.pyc \
		--exclude=*.log* \
		--exclude=out \
		. michael@bone:~/xbns
