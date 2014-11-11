import itertools


class Message(object):
    """Represents a message to be sent.

    - Handles conversion from string of bytes to int_array to matrix with a
    given number of rows.
    - Also handles padding and unpadding of initial message to fit in a matrix.
    """
    # Escape bytes
    END = 192
    ESCAPE = 219
    END_ESCAPED = (219, 220)
    ESCAPE_ESCAPED = (219, 221)

    def __init__(self, string):
        self.string = string

    def to_int_array(self):
        return [ord(x) for x in self.string]

    def to_matrix(self, rows):
        size = len(self.string)
        if size % rows != 0:
            size += rows
            size -= (size % rows)

        int_array = self.to_int_array()
        int_array = self.escape(int_array)
        int_array = self.addpadding(int_array, size)

        matrix = []
        idx = 0
        column = size/rows
        while idx < size:
            matrix.append(int_array[idx:idx + column])
            idx += column
        return matrix

    @classmethod
    def from_matrix(cls, matrix):
        int_array = list(itertools.chain(*matrix))
        int_array = [int(x) for x in int_array]
        int_array = cls.removepadding(int_array)
        int_array = cls.unescape(int_array)
        return cls.from_int_array(int_array)

    @classmethod
    def from_int_array(cls, int_array):
        return Message("".join(chr(x) for x in int_array))

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
