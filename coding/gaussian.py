class GaussianElimination(object):
    """Performs Gaussian elimination."""
    def __init__(self):
        self.a = []
        self.b = []
        self.x = None

    def add_row(self, a, b):
        if self.is_solved():
            return
        self.a.append(a)
        self.b.append(b)
        self._reduce()
        self._solve()

    def is_solved(self):
        return self.x is not None

    def get_rows_required(self):
        assert len(self.a) != 0
        return len(self.a[0]) - len(self.a)

    def solve(self):
        assert self.is_solved()
        return self.x

    def _swap(self, idx1, idx2):
        self.a[idx1], self.a[idx2] = self.a[idx2], self.a[idx1]
        self.b[idx1], self.b[idx2] = self.b[idx2], self.b[idx1]

    def _mul(self, idx, mul):
        self.a[idx] = [mul*elem for elem in self.a[idx]]
        self.b[idx] = [mul*elem for elem in self.b[idx]]

    def _add(self, row_from, mul, row_to):
        r1 = self.a[row_to]
        r2_mul = [mul*elem for elem in self.a[row_from]]
        self.a[row_to] = [r1[i] + r2_mul[i] for i in xrange(len(r1))]

        r1 = self.b[row_to]
        r2_mul = [mul*elem for elem in self.b[row_from]]
        self.b[row_to] = [r1[i] + r2_mul[i] for i in xrange(len(r1))]

    def _del(self, idx):
        del self.a[idx]
        del self.b[idx]

    def _solve(self):
        if len(self.a) != len(self.a[0]):
            return

        # Back substitution (should be in reduced row-echelon form now)
        rows = xrange(0, len(self.a))
        for idx in reversed(rows):
            for i in xrange(0, idx):
                if self.a[i][idx] == 0:
                    continue
                self._add(idx, -1.0 * self.a[i][idx], i)

        # Solved.
        self.x = self.b 

    def _reduce(self):
        if len(self.a) < 1:
            return

        # For each column, reduce.
        search_from_row = 0
        for j in xrange(len(self.a[0])):
            # Row with value in this col.
            rows = xrange(search_from_row, len(self.a))
            row = next((i for i in rows if self.a[i][j] != 0), None)
            if row is None:
                continue

            # Reduce to coefficient of 1 here.
            self._mul(row, 1.0 / self.a[row][j])

            # Subtract other rows.
            other_rows = (x for x in rows if x != row and self.a[x][j] != 0)
            for i in other_rows:
                self._add(row, -1.0 * self.a[i][j] / self.a[row][j], i)

            # Move current row to the top and continue reducing.
            self._swap(row, search_from_row)
            search_from_row += 1

        # Delete non-innovative rows.
        rows = xrange(0, len(self.a))
        for idx in reversed(rows):
            if all(x == 0 for x in self.a[idx]):
                self._del(idx)


def main():
    # For testing.
    g = GaussianElimination()
    g.add_row([3,2,1], [12])
    print g.get_rows_required()
    print g.is_solved()
    g.add_row([6,4,2], [24])
    print g.get_rows_required()
    print g.is_solved()
    g.add_row([1,2,4], [4])
    print g.get_rows_required()
    print g.is_solved()
    g.add_row([2,1,2], [36])
    print g.get_rows_required()
    print g.is_solved()
    print g.b

if __name__ == '__main__':
    main()