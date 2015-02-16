import itertools


class Message(object):
    """Represents a message to be sent.

    Handles padding and unpadding of initial message to fit in a certain size.
    """
    # Escape bytes
    END = 192
    ESCAPE = 219
    END_ESCAPED = (219, 220)
    ESCAPE_ESCAPED = (219, 221)

    def __init__(self, string):
        self.string = string
        self._int_array = self.escape(self.to_int_array(string))

    def __len__(self):
        return len(self._int_array)

    def _to_int_array(self, size):
        return self.addpadding(self._int_array, size)

    def to_size(self, size):
        assert len(self) <= size
        return self.int_array_to_string(self._to_int_array(size))

    @classmethod
    def from_string(cls, string):
        int_array = cls.to_int_array(string)
        int_array = cls.removepadding(int_array)
        int_array = cls.unescape(int_array)
        return cls(cls.int_array_to_string(int_array))

    @classmethod
    def to_int_array(cls, string):
        return [ord(x) for x in string]

    @classmethod
    def int_array_to_string(cls, int_array):
        return "".join(chr(x) for x in int_array)

    @classmethod
    def escape(cls, int_array):
        escaped = []
        for x in int_array:
            if x == cls.END:
                escaped.extend(cls.END_ESCAPED)
            elif x == cls.ESCAPE:
                escaped.extend(cls.ESCAPE_ESCAPED)
            else:
                escaped.append(x)
        return escaped

    @classmethod
    def unescape(cls, int_array):
        unescaped = []
        length = len(int_array) - 1
        idx = 0
        while idx <= length:
            if idx == length:
                unescaped.append(int_array[idx])
            elif int_array[idx] == cls.END_ESCAPED[0] and \
                    int_array[idx + 1] == cls.END_ESCAPED[1]:
                unescaped.append(cls.END)
                idx += 1
            elif int_array[idx] == cls.ESCAPE_ESCAPED[0] and \
                    int_array[idx + 1] == cls.ESCAPE_ESCAPED[1]:
                unescaped.append(cls.ESCAPE)
                idx += 1
            else:
                unescaped.append(int_array[idx])
            idx += 1
        return unescaped

    @classmethod
    def addpadding(cls, int_array, to_size):
        padding_len = to_size - len(int_array)
        if padding_len > 0:
            int_array.extend([cls.END] * padding_len)
        return int_array

    @classmethod
    def removepadding(cls, int_array):
        if cls.END in int_array:
            end_index = int_array.index(cls.END)
            int_array = int_array[:end_index]
        return int_array


    # Convinience methods for network coding messages.
    def to_matrix(self, rows):
        size = len(self.string)
        if size % rows != 0:
            size += rows
            size -= (size % rows)
        int_array = self._to_int_array(size)
        matrix = []
        idx = 0
        column = size / rows
        while idx < size:
            matrix.append(int_array[idx:idx + column])
            idx += column
        return matrix

    @classmethod
    def from_matrix(cls, matrix):
        int_array = list(itertools.chain(*matrix))
        int_array = [int(round(x)) for x in int_array]
        int_array = cls.removepadding(int_array)
        int_array = cls.unescape(int_array)
        return cls(cls.int_array_to_string(int_array))
