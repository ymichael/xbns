import gaussian
import message
import matrix


def main():
    h = 10
    coeffs = [
        [10, 16, 5, 3, 12, 4, 19, 4, 8, 14],
        [1, 15, 15, 17, 0, 20, 4, 11, 7, 9],
        [11, 9, 1, 2, 12, 17, 5, 2, 17, 8],
        [1, 14, 11, 3, 3, 8, 18, 2, 2, 7],
        [1, 19, 1, 11, 20, 5, 2, 9, 15, 8],
        [19, 11, 2, 7, 8, 11, 11, 20, 5, 7],
        [17, 5, 6, 6, 3, 13, 8, 4, 15, 20],
        [8, 9, 7, 5, 8, 18, 4, 14, 11, 3],
        [2, 20, 19, 4, 7, 13, 10, 7, 17, 14],
        [9, 18, 3, 15, 13, 0, 13, 5, 17, 11],
    ]
    data = "A wireless sensor network (WSN) of spatially distributed autonomous sensors to monitor physical or environmental conditions, such as temperature, sound, pressure, etc. and to cooperatively pass their data through the network to a main location. The more modern networks are bidirectional, also enabling control of sensor activity. The development of wireless sensor networks was motivated by military applications such as battlefield surveillance; today such networks are used in many industrial and consumer applications, such as industrial process monitoring and control, machine health monitoring, and so on."
    m = message.Message(data)
    rows = m.to_matrix(rows=h)
    data_mat = matrix.Matrix(rows)
    coeffs_mat = matrix.Matrix(coeffs)
    coded_mat = coeffs_mat.dot(data_mat)

    g = gaussian.GaussianElimination()
    for row_i in xrange(coeffs_mat.num_rows):
        g.add_row(
            list(coeffs_mat.iter_row(row_i)),
            list(coded_mat.iter_row(row_i)))
    solution = g.solve()
    x = message.Message.from_matrix(solution.rows)
    print x.string

if __name__ == '__main__':
    main()
