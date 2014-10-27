# XBee Networking Stack

An implmentation of various networking layers for a network of nodes connected
with XBee radios.

## Installing dependencies
```sh
$ pip install -r requirements.txt
```

## Running main.py
```sh
# See Makefile for more details.
python main.py \
	--panid=[PANID] \
	--channel=[CHANNEL] \
	--myid=[MYID] \
	--port=[SERIALPORT]
```

## Running tests
```sh
# Installing test runner.
$ pip install nose
$ pip install mockito

$ nosetests
```
