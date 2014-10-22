import base
import struct


class NetworkPDU(object):
    # https://docs.python.org/2/library/struct.html
    # B: unsigned char, 1 byte.
    # h: unsigned short, 2 bytes.
    # I: unsigned int, 4 bytes.
    # Q: unsigned long long, 8 bytes.
    HEADER_FORMAT = "hBII"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAX_DATA_SIZE = 100 - HEADER_SIZE

    @classmethod
    def serialize(cls, source_id, message_id, total_chunks, piece_no, chunk):
        header = struct.pack(cls.HEADER_FORMAT, source_id, message_id, total_chunks, piece_no)
        return header + chunk

    @classmethod
    def deserialize(cls, data):
        x = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        return (x[0], x[1], x[2], x[3], data[cls.HEADER_SIZE:])


class Network(base.BaseLayer):
    """Network layer.

    Converts variable sized data into fixed sized packets.
    """
    def __init__(self, id):
        super(Network, self).__init__()
        self.id = id
        self.last_message_id = 0
        self.buffer = {}

    def get_next_message_id(self):
        # restrict message id to be from 1 - 255
        self.last_message_id = (self.last_message_id + 1) % 255
        return self.last_message_id

    def process_incoming(self, data):
        self.deserialize_chunk(data)

    def process_outgoing(self, data):
        message_id = self.get_next_message_id()
        total_size = len(data)
        for idx, chunk in enumerate(self._chunk_data(data)):
            serialized_chunk = self.serialize_chunk(message_id, total_size, idx, chunk)
            self.outgoing_queue.put(serialized_chunk)

    def deserialize_chunk(self, serialized_chunk):
        source_id, message_id, total_size, piece_no, chunk = NetworkPDU.deserialize(serialized_chunk)
        key = (source_id, message_id)
        buffered_chunks = self.buffer.get(key, [])
        buffered_chunks.append((piece_no, chunk))
        buffered_chunks.sort()
        self.buffer[key] = buffered_chunks

        # If the final piece is in.
        size = sum((len(x[1]) for x in buffered_chunks))
        if size != total_size:
            return
        data = "".join((x[1] for x in buffered_chunks))
        self.incoming_queue.put(data)
        del self.buffer[key]

    def serialize_chunk(self, message_id, total_size, piece_no, chunk):
        return NetworkPDU.serialize(self.id, message_id, total_size, piece_no, chunk)

    def _chunk_data(self, data):
        """Chunk data into lengths no greater than MAX_DATA_SIZE."""
        chunks = []
        current_idx = 0
        while current_idx < len(data):
            chunk = data[current_idx:current_idx + NetworkPDU.MAX_DATA_SIZE]
            chunks.append(chunk)
            current_idx += NetworkPDU.MAX_DATA_SIZE
        return chunks

