XBee Networking Framework
=========================
A collection of tools used for managing a network of xbee connected devices.

## `net`
- An implmentation of a networking stack that works with xbees radios.
- Modelled after the OSI model
- Each layer has two `Queue.Queue` (incoming and outgoing)
- Each "consumer" runs on a separate thread (~2 threads per layer)
- Layers:
    - `net.layers.physical`: Interfaces with the radio
    - `net.layers.datalink`: Handles routing, forwarding and chunking (xbee frames take a max size of 100 bytes).
    - `net.layers.transport`: Handles multiplexing and demultiplexing between different applications layer programs.
    - `net.layers.application`: Base class for implementing application layer programs that use the networking stack.
- Communication between transport and application layer is via UNIX TCP/IP sockets (see `sock`).

## `net.radio`
- Abstraction over the xbee radio API to allow other applications (eg. `sim`) to swap out the radio class.

## `app`
- Contains various application level programs that make use of the `net` stack.

## `sim`
- A simple network simulator to that can be configured to run various network topologies and applications.
- Simulates shared medium using queues to send messages along predefined links.
- Tightly coupled with the networking stack to enable multiple "stacks" and "apps" to be run concurrently.
- Fake implementation of xbee radios

## `coding`
- Contains message encoding/decoding functions. (eg. padding, escaping etc.)
- Protocols typically require messages to be a fix size.
- Also contains Network Coding related operations:
    - Matrix methods
    - Gaussian Elimination
    - Finite Field arithmetic

## `utils`
- Contains various utility modules for remove management of nodes
- `cli`: Abstraction over the `subprocess` module.
- `git`: Helper functions to format and apply git patches and other git operations.
- `timespec`: Function to system time on beaglebones (which are assumed to neither have RTC nor connection to the Internet)

## Other
- `bin`: Scripts and `.service` files for systemd services to "install" on each device.
- `log`:
    - Log parsing scripts to combine and process logs from multiple nodes.
    - Extract "runs" (instances of a protocol) and output useful statistics.
    - Untidy but works for now.
- `sock`: Abstraction over UNIX TCP/IP sockets to expose a `Queue.Queue`-like interface so applications can treat both the same way.
- `xbee`: A third-party library version controlled for ease of deploying on beablebone devices

## Important files
- `addr.txt`: (gitignored) Contains the node ID, needs to be explicitly set per device.
- `Makefile`: Contains various targets for managing the entire framework.
- `config.py`: Configuration parameters shared by all nodes in the network.
- `setup.md`: Steps for setting up a beaglebone device from scratch.


## Installing dependencies

```sh
# pyserial, xbee
$ pip install -r requirements.txt
```

- `log` also uses `tabulate`, only required if parsing logs.

## Usage

See `setup.md` for beaglebone setup and `Makefile` for the relevant targets.

## Tests

```sh
# Installing test runner.
$ pip install nose
$ pip install mockito

$ nosetests
```
