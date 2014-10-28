import base
import struct


class DataLinkPDU(object):
    # source_addr: h
    # dest_addr: h
    # message_id: B
    # total_size: I
    # piece_number: I
    HEADER_FORMAT = "hhBII"
    # https://docs.python.org/2/library/struct.html
    # B: unsigned char, 1 byte.
    # h: unsigned short, 2 bytes.
    # I: unsigned int, 4 bytes.
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAX_DATA_SIZE = 100 - HEADER_SIZE

    def __init__(self, source_addr, dest_addr, message_id, total_size, piece_no, chunk):
        self.source_addr = source_addr
        self.dest_addr = dest_addr
        self.message_id = message_id
        self.total_size = total_size
        self.piece_no = piece_no
        self.chunk = chunk

    def to_string(self):
        header = struct.pack(self.HEADER_FORMAT, self.source_addr,
            self.dest_addr, self.message_id, self.total_size, self.piece_no)
        return header + self.chunk

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        return DataLinkPDU(x[0], x[1], x[2], x[3], x[4], data[cls.HEADER_SIZE:])


class DataLink(base.BaseLayer):
    """DataLink layer.

    Converts variable sized data into fixed sized packets.
    """
    def __init__(self, addr):
        super(DataLink, self).__init__()
        self.addr = addr
        self.last_message_id = 0
        self.buffer = {}

    def get_next_message_id(self):
        # restrict message id to be from 1 - 255
        self.last_message_id = (self.last_message_id + 1) % 255
        return self.last_message_id

    def _chunk_data(self, data):
        """Chunk data into lengths no greater than MAX_DATA_SIZE."""
        chunks = []
        current_idx = 0
        while current_idx < len(data):
            chunk = data[current_idx:current_idx + DataLinkPDU.MAX_DATA_SIZE]
            chunks.append(chunk)
            current_idx += DataLinkPDU.MAX_DATA_SIZE
        return chunks

    def process_outgoing(self, data, metadata=None):
        message_id = self.get_next_message_id()
        total_size = len(data)
        # TODO: Thread this through.
        dest_addr = 0
        for piece_no, chunk in enumerate(self._chunk_data(data)):
            data_unit = DataLinkPDU(self.addr, dest_addr, message_id, total_size,
                piece_no, chunk)
            self.put_outgoing(data_unit.to_string(), metadata)

    def process_incoming(self, data, metadata=None):
        data_unit = DataLinkPDU.from_string(data)
        # TODO: Add checksum/verify step.
        key = (data_unit.source_addr, data_unit.message_id)

        # TODO: Fix this. Use offset instead?
        buffered_chunks = self.buffer.get(key, [])
        buffered_chunks.append((data_unit.piece_no, data_unit.chunk))
        buffered_chunks.sort()
        self.buffer[key] = buffered_chunks
        # If the final piece is in.
        size = sum((len(x[1]) for x in buffered_chunks))
        if size == data_unit.total_size:
            del self.buffer[key]
            reformed_fragments = "".join((x[1] for x in buffered_chunks))
            self.put_incoming(reformed_fragments, metadata)

