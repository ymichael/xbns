import base
import struct


class DataLinkPDU(object):
    # source_addr: H
    # dest_addr: H
    # message_id: B
    # total_size: I
    # piece_number: I
    HEADER_FORMAT = "HHBII"
    # https://docs.python.org/2/library/struct.html
    # B: unsigned char, 1 byte.
    # H: unsigned short, 2 bytes.
    # I: unsigned int, 4 bytes.
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAX_DATA_SIZE = 100 - HEADER_SIZE

    def __init__(self, source_addr, dest_addr, message_id, total_size, piece_no,
            chunk):
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

    - Converts variable sized data into fixed sized packets.
    - Forwards packets along the network.
    """
    def __init__(self, addr):
        super(DataLink, self).__init__(addr)
        self.last_message_id = 0
        self.buffer = {}
        self.seen_buffer = set()
        self.forward_buffer = set()

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

        # Get values from metadata.
        dest_addr = base.MetaData.DEST_ADDR
        if metadata is not None:
            dest_addr = metadata.dest_addr

        for piece_no, chunk in enumerate(self._chunk_data(data)):
            data_unit = DataLinkPDU(self.addr, dest_addr, message_id,
                total_size, piece_no, chunk)
            self.put_outgoing(data_unit.to_string(), metadata)

    def _maybe_forward_data(self, data_unit):
        if data_unit.dest_addr == base.MetaData.BROADCAST_ADDR:
            return
        # Do not forward if we are the intended recipient.
        if data_unit.dest_addr == self.addr:
            return
        # Ignore packet if we've already received it.
        key = (data_unit.source_addr, data_unit.message_id,
            data_unit.piece_no)
        if key in self.forward_buffer:
            return
        # Forward packet if we've not seen this.
        # TODO: Add TTL and decrement?
        self.forward_buffer.add(key)
        self.put_outgoing(data_unit.to_string())

    def _maybe_buffer_incoming(self, data_unit, metadata=None):
        # Only buffer packets that are intended for us.
        if data_unit.dest_addr != base.MetaData.BROADCAST_ADDR and \
            data_unit.dest_addr != self.addr:
            return

        # Logging to see the packet loss rate.
        self.logger.debug("Incoming: %s, %s, %s" % \
            (data_unit.source_addr, data_unit.message_id, data_unit.piece_no))

        key = (data_unit.source_addr, data_unit.message_id)
        if key in self.seen_buffer:
            return
        buffered_chunks = self.buffer.get(key, {})
        buffered_chunks[data_unit.piece_no] = data_unit.chunk
        self.buffer[key] = buffered_chunks
        size = sum((len(x) for x in buffered_chunks.values()))
        if size == data_unit.total_size:
            del self.buffer[key]
            self.seen_buffer.add(key)
            keys = sorted(buffered_chunks.keys())
            data = "".join(buffered_chunks[x] for x in keys)
            # propagate metadata 
            metadata = metadata or base.MetaData()
            metadata.source_addr = data_unit.source_addr
            self.put_incoming(data, metadata)

    def process_incoming(self, data, metadata=None):
        data_unit = DataLinkPDU.from_string(data)
        # TODO: Add checksum/verify step.
        self._maybe_forward_data(data_unit)
        self._maybe_buffer_incoming(data_unit, metadata)
