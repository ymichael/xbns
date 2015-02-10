import matrix


class GaussianElimination(object):
    """Performs Gaussian elimination.

    Allows rows to be added in parts.
    """

    MATRIX_CLS = matrix.Matrix

    def __init__(self):
        self.a = self.MATRIX_CLS()
        self.b = self.MATRIX_CLS()
        self.solution = None

    def add_row(self, a, b):
        if self.is_solved():
            return
        self.a.add_row(list(a))
        self.b.add_row(list(b))
        self._reduce()
        self._solve()

    def is_solved(self):
        return self.solution is not None

    def solve(self):
        assert self.is_solved()
        return self.solution

    def get_rows_required(self):
        if self.a.num_rows == 0:
            return 0
        return self.a.num_cols - self.a.num_rows

    # 3 Types of operations
    # - Type 1: Swap the positions of two rows.
    # - Type 2: Divide a row by a nonzero scalar.
    # - Type 3: Subtract mul * row j from row i
    def _swap_rows(self, i, j):
        self.a.swap_rows(i, j)
        self.b.swap_rows(i, j)

    def _div_row(self, i, val):
        if val == 1:
            return
        self.a.div_row(i, val)
        self.b.div_row(i, val)

    def _sub_from_row(self, i, mul, j):
        if mul == 0:
            return
        self.a.sub_from_row(
            i, self.MATRIX_CLS.mul_values(self.a.iter_row(j), mul))
        self.b.sub_from_row(
            i, self.MATRIX_CLS.mul_values(self.b.iter_row(j), mul))

    def _remove_row(self, i):
        self.a.remove_row(i)
        self.b.remove_row(i)

    def _remove_non_innovative_rows(self):
        # Delete non-innovative rows, from the bottom.
        for row in xrange(self.a.num_rows - 1, -1, -1):
            if all(x == 0 for x in self.a.iter_row(row)):
                self._remove_row(row)

    def _first_row_with_val_in_col(self, starting_row, col):
        for row in xrange(starting_row, self.a.num_rows):
            if self.a.get(row, col) != 0:
                return row
        return None

    def _solve(self):
        if self.get_rows_required() != 0:
            return
        # Back substitution (should be in reduced row-echelon form now)
        for row in xrange(self.a.num_rows - 1, -1, -1):
            # Reduce all other rows (above the current row) to 0 where col = row.
            for other_row in xrange(0, row):
                multiple = self.a.get(other_row, row)
                self._sub_from_row(other_row, multiple, row)
        # Solved.
        self.solution = self.b.copy()

    def _reduce(self):
        current_row = 0
        # For each column, reduce every row to 0 but one and move it to the top.
        for col in xrange(self.a.num_cols):
            # Find a row with a non-zero value in this col
            row_with_value = self._first_row_with_val_in_col(current_row, col)
            if row_with_value is None:
                continue
            # Reduce row_with_value to coefficient of 1 here.
            self._div_row(row_with_value, self.a.get(row_with_value, col))
            # For other rows, subtract a multiple of row_with_value to have
            # value at col = 0.
            for other_row in xrange(row_with_value + 1, self.a.num_rows):
                multiple = self.a.get(other_row, col)
                self._sub_from_row(other_row, multiple, current_row)
            # Move current row to the top and continue reducing.
            self._swap_rows(row_with_value, current_row)
            current_row += 1

        self._remove_non_innovative_rows()
