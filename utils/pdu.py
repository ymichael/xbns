import struct


class PDUType(type):
    def __new__(cls, name, bases, attrs):
        # Assign indices for types
        if 'TYPES' in attrs:
            types = attrs['TYPES']
            for i in xrange(len(types)):
                attrs[types[i]] = i
            # Create INDEX_TO_TYPE mapping.
            assert 'INDEX_TO_TYPE' not in attrs
            attrs['INDEX_TO_TYPE'] = [t.lower() for t in types]
            # Create respective `classmethods` to create each message type.
            def generic_create(t): return lambda cls: cls(attrs[t.upper()])
            for t in attrs['INDEX_TO_TYPE']:
                if "create_" + t not in attrs:
                    attrs["create_" + t] = classmethod(generic_create(t))
        # Create `from_string` classmethod.
        def from_string(cls, data):
            x = struct.unpack(cls.HEADER_PREFIX, data[:cls.HEADER_PREFIX_SIZE])
            return cls(x[0], data[cls.HEADER_PREFIX_SIZE:])
        attrs["from_string"] = classmethod(from_string)
        return super(PDUType, cls).__new__(cls, name, bases, attrs)


class PDU(object):
    __metaclass__ = PDUType

    TYPES = []
    HEADER_PREFIX = "B" # B: unsigned char
    HEADER_PREFIX_SIZE = struct.calcsize(HEADER_PREFIX)

    def __init__(self, msg_type, message=""):
        self.msg_type = msg_type
        self.readable_msg_type = self.INDEX_TO_TYPE[msg_type]
        self.message = message
        if hasattr(self, "_init_" + self.readable_msg_type):
            return getattr(self, "_init_" + self.readable_msg_type)()

    def __getattr__(self, name):
        if name.startswith("is_"):
            return lambda: self.readable_msg_type == name[3:]
        raise AttributeError("%r object has no attribute %r" % (self.__class__, name))

    def __repr__(self):
        if hasattr(self, "_repr_" + self.readable_msg_type):
            return getattr(self, "_repr_" + self.readable_msg_type)()
        # Simply return the uppercased readable version of the message type.
        return self.type

    @property
    def type(self):
        return self.readable_msg_type.upper()

    def to_string(self):
        header = struct.pack(self.HEADER_PREFIX, self.msg_type)
        return header + self.message

