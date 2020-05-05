import State_Geneneration as SG
import numpy as np

# определяет относительный сдвиг для индексации гексагона по номеру слоя
base_hexes = [
    ((-2, -4), (-2, -4))  # i<5, even layer/odd layer
    , ((-3, -3), (-2, -3))  # i<11
    , ((-3, -2), (-3, -2))  # i<18
    , ((-4, -1), (-3, -1))  # i<26
    , ((-4, 0), (-4, 0))  # i<35
    , ((-4, 1), (-3, 1))  # i<43
    , ((-3, 2), (-3, 2))  # i<50
    , ((-3, 3), (-2, 3))  # i<56
    , (-2, 4), (-2, 4)  # i<61
]


def compute_units(player):
    units = np.zeros(4, "int")
    if player == 0:
        units[0] = SG.P1_unit1
        units[1] = SG.P1_unit2
        units[2] = SG.P1_unit3
        units[3] = SG.P1_unit4
    else:
        units[0] = SG.P2_unit1
        units[1] = SG.P2_unit2
        units[2] = SG.P2_unit3
        units[3] = SG.P2_unit4
    return units


# для ускорения работы эту функцию можно использовать один раз для составления таблицы по которой
# можно вычислять координаты точке
def compute_hex_by_layer(i, hex):
    odd = hex[1] % 2 != 0
    if i < 5:
        return base_hexes[0][odd][0] + hex[0] + i - 0, hex[1] + base_hexes[0][odd][1]
    if i < 11:
        return base_hexes[1][odd][0] + hex[0] + i - 5, hex[1] + base_hexes[1][odd][1]
    if i < 18:
        return base_hexes[2][odd][0] + hex[0] + i - 11, hex[1] + base_hexes[2][odd][1]
    if i < 26:
        return base_hexes[3][odd][0] + hex[0] + i - 18, hex[1] + base_hexes[3][odd][1]
    if i < 35:
        return base_hexes[4][odd][0] + hex[0] + i - 26, hex[1] + base_hexes[4][odd][1]
    if i < 43:
        return base_hexes[5][odd][0] + hex[0] + i - 35, hex[1] + base_hexes[5][odd][1]
    if i < 50:
        return base_hexes[6][odd][0] + hex[0] + i - 43, hex[1] + base_hexes[6][odd][1]
    if i < 56:
        return base_hexes[7][odd][0] + hex[0] + i - 50, hex[1] + base_hexes[7][odd][1]
    if i < 61:
        return base_hexes[8][odd][0] + hex[0] + i - 56, hex[1] + base_hexes[8][odd][1]

def isPlayerNearBy(hex,player):


def normalise_spend_order(order):#зануляем только черные так как другие
                                        #возможности зависят от порядка постороек:например можно
                                        #соединить провинции и тогда недоступные клетки станут доступны

    not_black=[]
    for i in range(len(order)):
        hex = i // SG.width, i % SG.width
        if SG.state[hex][SG.black] == 1:
            order[i] = 0
            continue
        not_black.append((hex,order[i]))
    return not_black


def get_action_distribution(player):
    # сейчас сгенерирую случайно(равномерно для доступных действий)
    activity_order = [0.5, 0.5]  # 0 - движение юнитов/1-трата денег
    field_size = SG.height * SG.width
    unit_movement_order = np.zeros(field_size) + 1.0 / field_size
    # нормальзация вектора ходов юнитов

    units = compute_units(player)

    hexes_with_units = []

    # получим матрицу ходов для юнитов
    actions = np.zeros((SG.height, SG.width, 61))
    mean = np.zeros(61)
    mean[:] = 1 / 61
    actions[:, :] = mean
    # проверка наличия юнита в клетке
    for i in range(field_size):
        hex = i // SG.width, i % SG.width
        state = SG.state
        if state[hex][units[0]] == 0 and state[hex][units[1]] == 0 \
                and state[hex][units[1]] == 0 and state[hex][units[0]] == 0:
            unit_movement_order[i] = 0
            actions[hex][:] = 0  # обнуление всех слоёв возможных ходов
        else:
            hexes_with_units.append((hex, unit_movement_order[i]))
    hexes_with_units = np.asarray(hexes_with_units)

    # после зануления невозможных вероятностей, перенормализуем вектор
    if len(hexes_with_units) != 0: hexes_with_units[:][1] = hexes_with_units[:][1] / hexes_with_units[:][1].sum()

    # Нормализация действий проходит по ходу семплирования порядка движения юнитов
    # Так как от порядка зависит возможность и не возможность последующих действий
    ######

    # генерация порядка траты денег
    hex_spend_order = np.zeros(field_size) + 1.0 / field_size
    mean1 = np.zeros(7)
    mean1[:] = 1 / 7
    spend_money_matrix = np.zeros((SG.height, SG.width, 7))
    spend_money_matrix[:, :] = mean1

    not_black_spend_hexes = normalise_spend_order(hex_spend_order)  # черные гексагоны отбрасываются

    return activity_order, unit_movement_order, actions, hexes_with_units, spend_money_matrix, not_black_spend_hexes, hex_spend_order


def fill_the_probabilities_of_actions(move, hex):  # принимает на вход массив из 61 одного
    # возможного хода и возвращает нормализованный

    return


def perform_one_unit_move(hex, player, unit):


def move_all_units(player, actions, hexes_with_units):
    order = []
    # семплирование порядка ходов:на кажом ходе выбирается юнит пропорционально его вероятности
    # затем он удаляется из списка и из остальных снова можно выбирать следующего
    for i in range(len(hexes_with_units)):
        r = np.random.random()
        s = 0
        for hex in hexes_with_units:
            s += hex[1]
            if r < s:
                order.append(hex)
                np.delete(hexes_with_units, hex)
                hexes_with_units[:][1] = hexes_with_units[:][1] / hexes_with_units[:][1].sum()
                break

    # на каждой итерации делается ход с учетом предыдущих итераций
    units = compute_units(player)
    for hex in order:
        actions[hex[0]], active_moves = fill_the_probabilities_of_actions(actions[hex[0]], hex[0])
        r = np.random.random()
        s = 0
        move = None
        # семплирование возможного хода
        for i in range(len(active_moves)):
            s += actions[hex[0], active_moves[i]]
            if r < s:
                move = active_moves[i]
        # making move
        move_to_hex = compute_hex_by_layer(move, hex[0])
        if SG.state[hex[0]][units[0]] == 1:
            perform_one_unit_move(move_to_hex, player, units[0])
        if SG.state[hex[0]][units[1]] == 1:
            perform_one_unit_move(move_to_hex, player, units[1])
        if SG.state[hex[0]][units[2]] == 1:
            perform_one_unit_move(move_to_hex, player, units[2])
        if SG.state[hex[0]][units[3]] == 1:
            perform_one_unit_move(move_to_hex, player, units[3])


def spend_all_money(player, spend_money_matrix, active_spend_hexes):


def make_move(player):
    activity_order, unit_movement_order, actions, hexes_with_units, \
    spend_money_matrix, not_black_spend_hexes, hex_spend_order = get_action_distribution(player)
    activity = np.random.random() > activity_order[0]  # семплирование действия
    if activity == 0:
        move_all_units(player, actions, hexes_with_units)
        spend_all_money(player, spend_money_matrix, not_black_spend_hexes)
    else:
        spend_all_money(player, spend_money_matrix, not_black_spend_hexes)
        move_all_units(player, actions, hexes_with_units)
    if len(SG.player1_hexes) == 1 or len(SG.player2_hexes) == 1:
        return 1
    return 0
