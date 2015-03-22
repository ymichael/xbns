.PHONY: start port rsync rmpyc rsync-makefile sim test app pong ping deluge rateless settime clearlogs setpower logs setup setaddr

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
	PYTHONPATH=. python app/pong.py --port=$(SERIALPORT)

toporeq:
	PYTHONPATH=. python app/pong.py -m toporeq --port=$(SERIALPORT)

topoflood:
	PYTHONPATH=. python app/pong.py -m topoflood --port=$(SERIALPORT)

upgrade:
	PYTHONPATH=. python app/pong.py -m upgrade --port=$(SERIALPORT)

make:
	PYTHONPATH=. python app/pong.py -m make --port=$(SERIALPORT) --target=$(TARGET)

ping:
	PYTHONPATH=. python app/pong.py -m ping --port=$(SERIALPORT)

logs:
	rsync -avz --exclude=*.py bone:~/xbns/log/ log/
	# scp bone:~/xbns/log/* log/

settime:
	PYTHONPATH=. python app/pong.py -m time --port=$(SERIALPORT)

setpower:
	PYTHONPATH=. python app/pong.py -m power --port=$(SERIALPORT) --value=$(POWER)

manager:
	PYTHONPATH=. python app/manager.py -f data/20KB.in $(ARGS)

ota:
	PYTHONPATH=. python app/ota.py $(ARGS)

sim:
	PYTHONPATH=. python sim/main.py $(ARGS)

test:
	PYTHONPATH=. nosetests

monitorlog:
	PYTHONPATH=. python log/monitor.py $(ARGS)

# rsync repository with beaglebone (w/o makefile)
rsync:
	rsync -avz \
		--include=*.py \
		--exclude=addr.txt \
		--exclude=log/*.txt \
		--exclude=.venv \
		--exclude=*.pyc \
		--exclude=*.DS_Store \
		--exclude=log/* \
		--exclude=out \
		. michael@bone:~/xbns

# Used to test pong app. remote make target execution.
yo:
	echo YO

setaddr:
	ssh michael@bone "echo $(ADDR) > ~/xbns/addr.txt"


## ON BEAGLEBONE.

# SETUP TARGETS.
installpong:
	./bin/install.sh pong.service

installxbns:
	./bin/install.sh xbns.service

installapps:
	./bin/install.sh apps.service

installota:
	./bin/install.sh ota.service

setup: installxbns installpong installapps installota
	ps aux | grep python

rmpyc:
	find . | grep -v .venv | grep .pyc | xargs -r rm

clearlogs:
	find log/ -type f | grep -v py | xargs -r rm

reset: clearlogs setup

reboot:
	reboot

