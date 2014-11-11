XBee Networking Stack
=====================

An implmentation of a networking stack for use with XBees radios.

## `net`
- Modelled after the OSI model
- Entry point is `stack.py`
- Each layer has two `Queue.Queue` (incoming and outgoing)
- Each "consumer" runs on a separate thread (~2 threads per layer)

## `sim`
- Used to simulate various network topologies
- Fake implementations of xbee radios
  (use queues to send messages along predefined links)

## `coding`
- Network Coding related operations
- Matrix methods, Gaussian Elimination etc.

## `app`
- Contains various application level protocols
  (that make use of the `net` stack)
- TODO

## Installing dependencies
```sh
# pyserial, xbee
$ pip install -r requirements.txt
```

## Usage
See `Makefile` for the relevant targets.

## Tests
```sh
# Installing test runner.
$ pip install nose
$ pip install mockito

$ nosetests
```
