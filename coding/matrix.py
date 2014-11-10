def assert_rows(mat, rows):
    assert num_rows(mat) == rows


def assert_cols(mat, cols):
    for row in mat:
        assert len(row) == cols

def num_cols(mat):
    return len(mat[0])


def num_rows(mat):
    return len(mat)


def dot(a, b):
    assert_cols(a, num_rows(b))
    result = []
    for i, row_a in enumerate(a):
        result_row = []
        for j in xrange(num_cols(b)):
            result_row.append(
                sum(a[i][k] * b[k][j] for k in xrange(num_rows(b))))
        result.append(result_row)
    return result
