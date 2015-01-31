import Queue as queue
import socket
import threading
import time


class Reader(object):
    """A wrapper around socket.socket to easily read incoming data."""

    BUFFER_SIZE = 1024

    SOCKET_BACKLOG = 1

    def __init__(self, socket):
        self.socket = socket
        self.q = queue.Queue()

    def get(self):
        return self.q.get()

    def start(self):
        incoming = threading.Thread(target=self._listen_for_incoming)
        incoming.setDaemon(True)
        incoming.start()

    def _listen_for_incoming(self):
        # Listen on socket for outgoing messages from other applications.
        self.socket.listen(self.SOCKET_BACKLOG)
        while True:
            conn, client_address = self.socket.accept()
            try:
                chunks = [x for x in conn.recv(self.BUFFER_SIZE)]
                self.q.put("".join(chunks))
            finally:
                conn.close()


def main():
    # Create socket object.
    server_address = ('', 10000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(server_address)

    # Create read socket and 
    r = Reader(sock)
    r.start()

    while True:
        data = r.get()
        print data


if __name__ == '__main__':
    main()
