import Queue as queue
import socket
import threading
import time


class BufferedWriter(threading.Thread):
    def __init__(self, socket_address):
        super(BufferedWriter, self).__init__()
        self.daemon = True
        self.socket_address = socket_address
        self._queue = queue.Queue()

    def put(self, data):
        self._queue.put(data)

    def run(self):
        while True:
            data = self._queue.get()
            with Writer(self.socket_address) as w:
                w.write(data)


class Writer(object):
    def __init__(self, socket_address):
        self.socket_address = socket_address

    def __enter__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(self.socket_address)
        return self

    def write(self, data):
        self.socket.sendall(data)

    def __exit__(self, type, value, traceback):
        self.socket.close()


def main():
    server_address = ('', 10000)
    with Writer(server_address) as w:
        w.write("This is a message")

    
if __name__ == '__main__':
    main()