import base
import struct


class DataLinkPDU(object):
    # source_addr: H
    # dest_addr: H
    # message_id: B
    # ttl: B
    # total_size: I
    # piece_number: I
    HEADER_FORMAT = "HHBBII"
    # https://docs.python.org/2/library/struct.html
    # B: unsigned char, 1 byte.
    # H: unsigned short, 2 bytes.
    # I: unsigned int, 4 bytes.
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAX_DATA_SIZE = 100 - HEADER_SIZE

    def __init__(self, source_addr, dest_addr, message_id, ttl, total_size,
            piece_no, chunk):
        self.source_addr = source_addr
        self.dest_addr = dest_addr
        self.message_id = message_id
        self.total_size = total_size
        self.piece_no = piece_no
        self.chunk = chunk
        self.ttl = ttl

    def to_string(self):
        header = struct.pack(
            self.HEADER_FORMAT,
            self.source_addr, self.dest_addr,
            self.message_id, self.ttl,
            self.total_size, self.piece_no)
        return header + self.chunk

    @classmethod
    def from_string(cls, data):
        x = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        return DataLinkPDU(x[0], x[1], x[2], x[3], x[4], x[5], data[cls.HEADER_SIZE:])


class DataLink(base.BaseLayer):
    """DataLink layer.

    - Converts variable sized data into fixed sized packets.
    - Forwards packets along the network.
    """
    def __init__(self, ttl=0, buffer_window=10):
        super(DataLink, self).__init__()
        self.last_message_id = 0

        # Maximum number of hops to forward a message.
        self.ttl = ttl

        # Buffer of pieces: buffer[source_addr][message_id][piece_no]
        self.buffer = {}

        # Number of previous messages to keep around.
        self.buffer_window = buffer_window

    def get_next_message_id(self):
        # restrict message id to be from 1 - 255
        self.last_message_id = (self.last_message_id % 255) + 1
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

        # Get values from metadata.
        dest_addr = base.MetaData.DEST_ADDR
        if metadata is not None:
            dest_addr = metadata.dest_addr

        for piece_no, chunk in enumerate(self._chunk_data(data)):
            data_unit = DataLinkPDU(
                self.addr, dest_addr, message_id, self.ttl,
                total_size, piece_no, chunk)
            self.put_outgoing(data_unit.to_string(), metadata)

    def process_incoming(self, data, metadata=None):
        data_unit = DataLinkPDU.from_string(data)

        # Ignore packet if we've already received it.
        sender = data_unit.source_addr
        m_id = data_unit.message_id
        p_no = data_unit.piece_no
        if sender not in self.buffer:
            self.buffer[sender] = {}
        if m_id not in self.buffer[sender]:
            self.buffer[sender][m_id] = {}
        if p_no in self.buffer[sender][m_id]:
            return

        self._maybe_forward_data(data_unit)
        self._maybe_buffer_incoming(data_unit, metadata)

    def _maybe_forward_data(self, data_unit):
        if data_unit.dest_addr == base.MetaData.BROADCAST_ADDR:
            return
        # Do not forward if we are the intended recipient.
        if data_unit.dest_addr == self.addr:
            return
        # Do not forward if ttl is less than 1.
        if data_unit.ttl <= 0:
            return

        # Forward packet.
        data_unit.ttl -= 1
        self.put_outgoing(data_unit.to_string())

    def _maybe_buffer_incoming(self, data_unit, metadata=None):
        # Only buffer packets that are intended for us.
        if data_unit.dest_addr != base.MetaData.BROADCAST_ADDR and \
            data_unit.dest_addr != self.addr:
            return

        sender = data_unit.source_addr
        m_id = data_unit.message_id
        p_no = data_unit.piece_no
        self.buffer[sender][m_id][p_no] = data_unit.chunk
        buffered_chunks = self.buffer[sender][m_id]

        size = sum((len(x) for x in buffered_chunks.values()))
        if size == data_unit.total_size:
            keys = sorted(buffered_chunks.keys())
            data = "".join(buffered_chunks[x] for x in keys)
            # propagate metadata
            metadata = metadata or base.MetaData()
            metadata.source_addr = data_unit.source_addr
            self.put_incoming(data, metadata)

            # clear buffer
            self._clear_buffer(sender, m_id)

    def _clear_buffer(self, sender, message_id):
        # Remove all messages older than (sender, message_id - 10)
        min_m_id = (message_id - self.buffer_window) % 255
        for m_id in self.buffer[sender].keys():
            if min_m_id <= m_id <= message_id:
                continue
            del self.buffer[sender][m_id]




















