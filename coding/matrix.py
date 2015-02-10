class InvalidMatrixException(Exception):
    pass


class InvalidRowSizeException(Exception):
    pass


class Matrix(object):
    def __init__(self, rows=None):
        rows = rows or []
        row_sizes = {len(row) for row in rows}
        if len(row_sizes) > 1:
            raise InvalidMatrixException("Multiple row sizes found: %s" % row_sizes)
        self.rows = rows

    @property
    def num_rows(self):
        return len(self.rows)

    @property
    def num_cols(self):
        if self.num_rows:
            return len(self.rows[0])

    def get(self, row, col):
        assert row < self.num_rows
        assert col < self.num_cols
        return self.rows[row][col]

    def dot(self, other):
        assert isinstance(other, Matrix)
        assert self.num_cols == other.num_rows, \
            "Trying to multiply a %sx%s matrix with %sx%s matrix" % \
            (self.num_rows, self.num_cols, other.num_rows, other.num_cols)
        return self.copy()._dot(other)

    def _dot(self, other):
        new_rows = []
        for i in xrange(self.num_rows):
            new_row = []
            for j in xrange(other.num_cols):
                new_row.append(
                    self.vector_dot_product(self.iter_row(i), other.iter_col(j)))
            new_rows.append(new_row)
        self.rows = new_rows
        return self

    def iter_col(self, col):
        assert col < self.num_cols
        return (self.rows[row][col] for row in xrange(self.num_rows))

    def iter_row(self, row):
        assert row < self.num_rows
        return (self.rows[row][col] for col in xrange(self.num_cols))

    def add_row(self, row):
        if len(self.rows) != 0 and len(self.rows[0]) != len(row):
            raise InvalidRowSizeException(
                "Expected: %s, given: %s" % (len(self.rows[0]), len(row)))
        self.rows.append(row)

    def remove_row(self, row):
        assert row < self.num_rows
        del self.rows[row]

    def swap_rows(self, a, b):
        assert a < self.num_rows and b < self.num_rows
        self.rows[a], self.rows[b] = self.rows[b], self.rows[a]

    def mul(self, x):
        for row in xrange(self.num_rows):
            self.mul_row(row, x)

    def mul_row(self, row, x):
        assert row < self.num_rows
        self.rows[row][:] = self.mul_values(self.rows[row], x)

    def div(self, x):
        for row in xrange(self.num_rows):
            self.div_row(row, x)

    def div_row(self, row, x):
        assert row < self.num_rows
        self.rows[row][:] = [elem / float(x) for elem in self.rows[row]]

    def add_to_row(self, row, values):
        assert row < self.num_rows
        assert len(values) == self.num_cols
        self.rows[row][:] = [a + b for a, b in zip(self.rows[row], values)]

    def sub_from_row(self, row, values):
        assert row < self.num_rows
        assert len(values) == self.num_cols
        self.rows[row][:] = [a - b for a, b in zip(self.rows[row], values)]

    def __eq__(self, other):
        if not (isinstance(other, Matrix) and \
                self.num_rows == other.num_rows and \
                self.num_cols == other.num_cols):
            return False
        for i in xrange(self.num_rows):
            if self.rows[i] != other.rows[i]:
                return False
        return True

    def copy(self):
        return self.__class__([row[:] for row in self.rows])

    @staticmethod
    def mul_values(values, x):
        return [v * x for v in values]

    @staticmethod
    def vector_dot_product(a, b):
        return sum(x * y for x, y in zip(a, b))
