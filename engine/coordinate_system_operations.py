# определяет относительный сдвиг для индексации гексагона по номеру слоя
base_hexes = [
    ((-2, -4), (-2, -4)),  # i<5, even layer/odd layer
    ((-3, -3), (-2, -3)),  # i<11
    ((-3, -2), (-3, -2)),  # i<18
    ((-4, -1), (-3, -1)),  # i<26
    ((-4, 0), (-4, 0)),  # i<35
    ((-4, 1), (-3, 1)),  # i<43
    ((-3, 2), (-3, 2)),  # i<50
    ((-3, 3), (-2, 3)),  # i<56
    ((-2, 4), (-2, 4)),  # i<61
]


# для ускорения работы эту функцию можно использовать один раз для составления таблицы, по которой
# можно вычислять координаты точки
def compute_hex_by_layer(i, hexagon):
    """

    :param i: номер возможного гексагона, в который можно перейти из данного
    :param hexagon: гексагон, в котором находится юнит
    :return: гексагон, соответсвующий номеру
    """
    odd = hexagon[1] % 2 != 0
    if i < 5:
        return (
            base_hexes[0][odd][0] + hexagon[0] + i - 0,
            hexagon[1] + base_hexes[0][odd][1],
        )
    if i < 11:
        return (
            base_hexes[1][odd][0] + hexagon[0] + i - 5,
            hexagon[1] + base_hexes[1][odd][1],
        )
    if i < 18:
        return (
            base_hexes[2][odd][0] + hexagon[0] + i - 11,
            hexagon[1] + base_hexes[2][odd][1],
        )
    if i < 26:
        return (
            base_hexes[3][odd][0] + hexagon[0] + i - 18,
            hexagon[1] + base_hexes[3][odd][1],
        )
    if i < 35:
        return (
            base_hexes[4][odd][0] + hexagon[0] + i - 26,
            hexagon[1] + base_hexes[4][odd][1],
        )
    if i < 43:
        return (
            base_hexes[5][odd][0] + hexagon[0] + i - 35,
            hexagon[1] + base_hexes[5][odd][1],
        )
    if i < 50:
        return (
            base_hexes[6][odd][0] + hexagon[0] + i - 43,
            hexagon[1] + base_hexes[6][odd][1],
        )
    if i < 56:
        return (
            base_hexes[7][odd][0] + hexagon[0] + i - 50,
            hexagon[1] + base_hexes[7][odd][1],
        )
    if i < 61:
        return (
            base_hexes[8][odd][0] + hexagon[0] + i - 56,
            hexagon[1] + base_hexes[8][odd][1],
        )
