import State_Geneneration as SG
import numpy as np
from collections import deque

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
player = 0
player_provinces = {}
player_ambar_cost = {}
player_dict = {}
adversary_dict = {}
units = []


def compute_hex_by_layer(i, hex):
    """

    :param i: номер возможного гексагона, в который можно перейти из данного
    :param hex: гексагон, в котором находится юнит
    :return: гексагон, соответсвующий номеру
    """
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


def compute_units():
    global units
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


hex_by_layer = {}


# для ускорения работы эту функцию можно использовать один раз для составления таблицы по которой
# можно вычислять координаты точке


def get_action_distribution():
    """
    Возвращает полное распределение вероятностей для хода из данного состояния. Данные здесь не
    нормализуются. Выдаются вероятности с каким-то распределением. Лишь во время семплирования действий
    возможна нормальизация.
    :return:
    activity_order - порядок в котором выполняются группа действий: сначала ход всеми юнитами или
    сначала потратить все деньги
    actions - из данной клетки юнит может перейти в 61 другую(включая эту же). Для задания вероятностей
    переходов используется массив (board_width, board_height, 61)
    hexes_with_units - массив указывающий в каких гексагонах были юниты в начале хода(может изменяться
    по мере семплирования). Это список пар: гексагон и вероятность сходить из этой клетки
    spend_money_matrix - деньги в каждом гексагоне можно потратить 7-ю способами. Эта матрица задаёт
    вероятности соответсвующих трат
    hex_spend_order - порядок в котором будут обходиться клетки, в которых будут потрачены деньги.
    """
    # сейчас сгенерирую случайно(равномерно для доступных действий)
    activity_order = [0.5, 0.5]  # 0 - движение юнитов/1-трата денег
    field_size = SG.height * SG.width
    unit_movement_order = np.zeros(field_size) + 1.0 / field_size
    # нормальзация вектора ходов юнитов

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

    return activity_order, actions, hexes_with_units, spend_money_matrix, hex_spend_order


def BFS_for_connectivity(hexagon):
    """
    Получает все возможные гексагоны, доступные из данного. Включая серые и вражеские. Недоступные вражеские зануляются отдельно.
    :param hexagon: Гексагон, из которого начинается поиск
    :return: список достижимых гексагонов
    """
    steps = 4
    queue = deque()
    reachable_hexes = []
    reached = np.zeros((9, 9), bool)
    # 26-ой слой задаёт верхний гексагон в круге потенциально доступных гексагонов
    shiftX = compute_hex_by_layer(26, hexagon)[0]  # задаёт нуль отсчёта по оси X
    shiftY = compute_hex_by_layer(0, hexagon)[1]  # задаёт нуль отсчёта по оси Y

    queue.append((hexagon, steps))
    reached[hexagon[0] - shiftX, hexagon[1] - shiftY] = True
    reachable_hexes.append(hexagon)
    while len(queue) != 0:
        hex, step = queue.popleft()
        if step != 0:
            for i in range(6):
                adj = SG.getAdjecentHex(hex, i)
                if adj is not None and reached[adj[0] - shiftX, adj[1] - shiftY] == 0 and SG.state[adj][SG.black] != 1:
                    if SG.state[adj][player_dict["player_hexes"]] != 1:
                        reachable_hexes.append(adj)
                        reached[adj[0] - shiftX, adj[1] - shiftY] = True
                    else:
                        reached[adj[0] - shiftX, adj[1] - shiftY] = True
                        reachable_hexes.append(adj)
                        queue.append((adj, step - 1))

    return reachable_hexes


def normalise_the_probabilities_of_actions(move, hex):
    """
    принимает на вход массив из 61 одного возможного хода и возвращает нормализованный(занулены невозможные ходы и вектор перенормирован)
    Условия, при которых в гексагон перейти нельзя:
    1)Он является чёрной, в ней есть наш амбар или центр города. Нужно проверить защиту этой клетки.
    2)Рядом должна быть дружественная клетка, либо она сама дружественная
    3)Добраться до этого гексагона юнит может только по своим клеткам(нужно проверить есть ли путь)
    4)Если в целевом гексагоне есть дружественный юнит, нужно проверить возможность слияния.
    Если хотя бы одно из условий выше не выполнено, такой ход зануляется.
    :param move: распределение вероятностей его возможных ходов
    :param hex: гексагон, в котором стоит юнит
    :return: возвращает пару: нормализованный вектор действий и список возможных ходов
    """
    state = SG.state
    # Имеет смысл сделать поиск в ширину из данного гексагона и определить гексаноны, до которых есть путь.
    # определение тип юнита в клетке:
    unit_type = 1
    # 1 - крестьянин
    # 2 - копейщик
    # 3 - воин
    # 4 - рыцарь
    active_moves = []
    for i in range(4):
        if state[hex][units[i]] == 1:
            unit_type = i + 1
            break
    reachable_hexes = set(BFS_for_connectivity(hex))

    for i in range(61):
        hex_to_go = compute_hex_by_layer(i, hex)
        if i == 30:continue#случай, когда остаёмся на месте
        if hex_to_go not in reachable_hexes or (state[hex_to_go][player_dict["player_hexes"]] == 1
                                                and (state[hex_to_go][player_dict["ambar"]] == 1
                                                     or state[hex_to_go][player_dict["tower1"]] == 1
                                                     or state[hex_to_go][player_dict["tower2"]] == 1
                                                     or state[hex_to_go][player_dict["town"]] == 1)):
            move[i] = 0
            continue
        # далее проверка не стоит ли в целевой клетке наш юнит

        if state[hex_to_go][player_dict["player_hexes"]] == 1:
            frendly_unit = get_frendly_unit(hex_to_go)
            if frendly_unit is not None and unit_type + frendly_unit > 4:
                move[i] = 0
                continue

        # далее проверка защищённости, если клетка вражеская

        if state[hex_to_go][adversary_dict["player_hexes"]] == 1:
            if unit_type <= get_enemy_hex_defence(hex_to_go):
                move[i] = 0
                continue
        active_moves.append(i)

    sum = move.sum()
    if sum != 0:
        return move[:] / move.sum(), active_moves
    else:
        return move, active_moves


def get_enemy_hex_defence(hex):
    """
    Возвращает силу, с которой защищается вражеский гексагон
    :param hex:
    :return:
    """
    power = 0
    for i in range(6):
        adj = SG.getAdjecentHex(hex, i)
        if adj is None: continue
        power = max(power, get_enemy_unit(adj), get_enemy_building(adj))
    return max(power, get_enemy_unit(hex), get_enemy_building(hex))


def get_enemy_building(hex):
    """
    Возращает силу защиты клетки зданием
    :param hex:
    :return:
    """
    state = SG.state
    if state[hex][adversary_dict["town"]] == 1: return 1
    if state[hex][adversary_dict["tower1"]] == 1: return 2
    if state[hex][adversary_dict["tower2"]] == 1: return 3
    return 0


def get_enemy_unit(hex):
    """
    Возвражает тип вражеского юнита в клетке
    :param hex:
    :return:
    """
    state = SG.state
    if state[hex][adversary_dict["unit1"]] == 1: return 1
    if state[hex][adversary_dict["unit2"]] == 1: return 2
    if state[hex][adversary_dict["unit3"]] == 1: return 3
    if state[hex][adversary_dict["unit4"]] == 1: return 4
    return 0


def get_frendly_unit(hex):
    """
    Возвращает юнита из дружественной клетки.
    :param hex: гексагон в котором нужно найти юнита
    :return: Тип юнита в клетке. Если его там нет, возвращает 0
    """
    state = SG.state
    if state[hex][units[0]] == 1: return 1
    if state[hex][units[1]] == 1: return 2
    if state[hex][units[2]] == 1: return 3
    if state[hex][units[3]] == 1: return 4
    return None


def perform_one_unit_move(destination_hex, unit_type, unit_index):
    """
    Перемещает дружественный юнит в соответсвующую клетку, изменяя при этом состояние игры, соответвующе
    :param destination_hex: Целевой гексагон
    :param unit_type: Тип юнита
    :param unit_index: Его индекс в массиве состояний
    :return:
    """



def move_all_units(actions, hexes_with_units):
    """


    :param actions:
    :param hexes_with_units:
    :return:
    """
    order = []
    # семплирование порядка ходов:на кажом ходе выбирается юнит пропорционально его вероятности
    # затем он удаляется из списка и из остальных снова можно выбирать следующего

    # здесь предполагается, что в течении хода юниты которые не двигались продолжат оставаться в своих клетках
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

    for hex in order:
        actions[hex[0]], active_moves = normalise_the_probabilities_of_actions(actions[hex[0]], hex[0])
        r = np.random.random()
        s = 0
        move = None
        # семплирование возможного хода
        for i in range(len(active_moves)):
            s += actions[hex[0], active_moves[i]]
            if r < s:
                move = active_moves[i]
        # making move
        if  move is not None:
            if move == 30:continue#случай, когда стоим на месте
            move_to_hex = compute_hex_by_layer(move, hex[0])
            if SG.state[hex[0]][units[0]] == 1:
                perform_one_unit_move(move_to_hex, 1,units[0])
            if SG.state[hex[0]][units[1]] == 1:
                perform_one_unit_move(move_to_hex, 2,units[1])
            if SG.state[hex[0]][units[2]] == 1:
                perform_one_unit_move(move_to_hex, 3,units[2])
            if SG.state[hex[0]][units[3]] == 1:
                perform_one_unit_move(move_to_hex, 4,units[3])


def near_provinces(hex):
    """

    :param hex: текущий гексагон
    :return: Возвращает три значения: Наличие провинции рядом, список пар соседнего гексагона и номера его провинции,
     все соседние гексагоны
    """
    near_hex = []
    adjacentHex = []
    for i in range(6):
        adj = SG.getAdjecentHex(hex, i)
        if adj is None: continue
        adjacentHex.append(hex)
        if SG.state[hex][player_dict["player_hexes"]] == 1:
            near_hex.append(adj)
    if len(near_hex) == 0: return False, None, None

    hex_province_pair = []

    for hex in near_hex:
        for i in player_provinces:
            if hex in player_provinces[i]:
                hex_province_pair.append((hex, i))
    return True, hex_province_pair, adjacentHex


def normalise_the_probabilities_of_spending(actions, hex):
    # unit 1 = 10              0
    # small tower cost = 15   1
    # unit 2 = 20              2
    # unit 3 = 30              3
    # big tower cost = 35     4
    # unit 4 = 40              5
    # ambar cost зависит от текущего состояния и задаётся словарём

    # Есть тонкая важная проблема: что если на серый гексагон претендуют(находятся рядом) несколько провинций
    # будем считать что влюбом случает эти провинции объединятся и почти не важно кто их объединил
    # будем выбивать из двух возмножных акторов, того у кого больше сейчас денег, например
    active_actions = []

    # случай когда мы в уже к какой-то провинции:
    if SG.state[hex][player_dict["player_hexes"]] == 1:
        pronice = None
        for i in player_provinces:
            if hex in player_provinces[i]:
                pronice = i
        ##Проверим не занята ли эта позиция, а если занята юнитом то можно
        if SG.state[hex][player_dict["tower2"]] == 1 or \
                SG.state[hex][player_dict["ambar"]] == 1 or SG.state[hex][player_dict["unit4"]] == 1:
            actions[:] = 0
            return None, actions, active_actions

        money = SG.state[hex][player_dict["money"]]
        if SG.state[hex][player_dict["tower1"]] == 1:
            if money < 35:
                return None, actions, active_actions
            else:
                actions[:4] = 0
                actions[4] = 1
                actions[5:] = 0
                active_actions += [4]
                return (hex, pronice), actions, active_actions

        if SG.state[hex][player_dict["unit1"]] == 1 or SG.state[hex][player_dict["unit2"]] == 1 \
                or SG.state[hex][player_dict["unit3"]] == 1:
            actions[1] = 0
            actions[4:] = 0
        if money < 10:
            actions[:] = 0
            return None, actions, []
        isBarnNear = False
        if actions[6] != 0:
            adjacent_hexes = []
            for i in range(6):
                adj = SG.getAdjecentHex(hex, i)
                if adj is None: continue
                adjacent_hexes.append(hex)
            for hex0 in adjacent_hexes:
                if SG.state[hex0][player_dict["ambar"]] == 1: isBarnNear = True
        if player_ambar_cost[pronice] > money and not isBarnNear:
            actions[6] = 0
        else:
            if actions[6] != 0:
                active_actions.append(6)

        if money < 15:
            actions[1:6] = 0
            active_actions += [0]
            return (hex, pronice), actions[:] / actions[:].sum(), active_actions
        if money < 20:
            actions[2:6] = 0
            if actions[1] != 0:
                active_actions += [0, 1]
            else:
                active_actions += [0]

            return (hex, pronice), actions[:] / actions[:].sum(), active_actions
        if money < 30:
            actions[3:6] = 0
            if actions[1] != 0:
                active_actions += [0, 1, 2]
            else:
                if SG.state[hex][player_dict["unit3"]] == 1:
                    active_actions += [0]
                    actions[1:] = 0
                else:
                    active_actions += [0, 2]
            return (hex, pronice), actions[:] / actions[:].sum(), active_actions
        if money < 35:
            actions[4:6] = 0
            if actions[1] != 0:
                active_actions += [0, 1, 2, 3]
            else:
                if SG.state[hex][player_dict["unit3"]] == 1:
                    actions[1:] = 0
                    active_actions += [0]
                if SG.state[hex][player_dict["unit2"]] == 1:
                    actions[3:] = 0
                    active_actions += [0, 2]
                if SG.state[hex][player_dict["unit1"]] == 1:
                    actions[4:] = 0
                    active_actions += [0, 2, 3]
            return (hex, pronice), actions[:] / actions[:].sum(), active_actions
        if money < 40:
            actions[5:6] = 0
            if actions[1] != 0:
                active_actions += [0, 1, 2, 3, 4]
            else:
                if SG.state[hex][player_dict["unit3"]] == 1:
                    actions[1:] = 0
                    active_actions += [0]
                if SG.state[hex][player_dict["unit2"]] == 1:
                    actions[3:] = 0
                    active_actions += [0, 2]
                if SG.state[hex][player_dict["unit1"]] == 1:
                    actions[4:] = 0
                    active_actions += [0, 2, 3]
            return (hex, pronice), actions[:] / actions[:].sum(), active_actions
        if actions[1] != 0:
            active_actions += [0, 1, 2, 3, 4, 5]
        else:
            if SG.state[hex][player_dict["unit3"]] == 1:
                actions[1:] = 0
                active_actions += [0]
            if SG.state[hex][player_dict["unit2"]] == 1:
                actions[3:] = 0
                active_actions += [0, 2]
            if SG.state[hex][player_dict["unit1"]] == 1:
                actions[4:] = 0
                active_actions += [0, 2, 3]
        return (hex, pronice), actions[:] / actions[:].sum(), active_actions

    isProvinseNearby, adjacent_hex_province_pair, adjacent_hexes = near_provinces(hex)
    if not isProvinseNearby:
        actions[:] = 0
        return actions, active_actions
    # далее нужно разобраться находится ли гексагон во вражеской провинции, и действовать с учётом ближайших дружественных клеток

    # найдем провинцию от имени которой действуем по принципу максимального числа денег
    max = -10000
    active_pair = None
    for pair in adjacent_hex_province_pair:
        if SG.state[pair[0]][player_dict["money"]] > max:
            active_pair = pair
            max = SG.state[pair[0]][player_dict["money"]]
    money = SG.state[active_pair[0]][player_dict["money"]]
    actions[6] = 0  # амбар
    actions[1] = 0  # Башни
    actions[4] = 0
    isGray = SG.state[hex][SG.general_dict["gray"]] == 1
    if isGray:
        if money < 10:
            actions[:] = 0
            return None, actions, []
        if money < 15:
            actions[1:6] = 0
            active_actions += [0]
            return active_pair, actions[:] / actions.sum(), active_actions
        if money < 30:
            actions[3:6] = 0
            active_actions += [0, 2]
            return active_pair, actions[:] / actions.sum(), active_actions
        if money < 40:
            actions[5] = 0
            active_actions += [0, 2, 3]
            return active_pair, actions[:] / actions.sum(), active_actions
        # больше или равно 40 монет
        active_actions += [0, 2, 3, 5]
        return active_pair, actions[:] / actions.sum(), active_actions

    # найдем силу защищающую клетку
    power = -4
    for hex0 in adjacent_hexes:


def spend_money_on_hex(hex, action):


def spend_all_money(spend_money_matrix):
    order = []
    for i in range(len(not_black_spend_hexes)):
        r = np.random.random()
        s = 0
        for hex in not_black_spend_hexes:
            s += hex[1]
            if r < s:
                order.append(hex)
                np.delete(not_black_spend_hexes, hex)
                not_black_spend_hexes[:][1] = not_black_spend_hexes[:][1] / not_black_spend_hexes[:][1].sum()
                break
    # order : каждый элемент это гексагон+его вероятность
    for hex in order:
        spend_money_matrix[hex[0]], active_actions = normalise_the_probabilities_of_spending(player,
                                                                                             spend_money_matrix[hex[0]],
                                                                                             hex[0])
        r = np.random.random()
        s = 0
        action = None
        # семплирование возможного хода
        for i in range(len(active_actions)):
            s += spend_money_matrix[hex[0], active_actions[i]]
            if r < s:
                action = active_actions[i]
        if not action is None: spend_money_on_hex(hex[0], action)


def make_move(move_player):
    """
    Совершает ход игроком
    :param move_player: 0 если первый игрок, 1 если второй
    :return: возвращает 1, если у одного из игроков закончились провинции. Иначе 0
    """
    global player_dict, adversary_dict, player_provinces, player_ambar_cost, player, units
    if move_player == 0:
        player = 0
        player_dict = SG.P1_dict
        adversary_dict = SG.P2_dict
        player_provinces = SG.player1_provinces
        player_ambar_cost = SG.player1_province_ambar_cost
        units = compute_units()
    else:
        player = 1
        player_dict = SG.P2_dict
        adversary_dict = SG.P1_dict
        player_provinces = SG.player2_provinces
        player_ambar_cost = SG.player2_province_ambar_cost
        units = compute_units()

    activity_order, actions, hexes_with_units, \
    spend_money_matrix, hex_spend_order = get_action_distribution()
    activity = np.random.random() > activity_order[0]  # семплирование действия
    if activity == 0:
        move_all_units(actions, hexes_with_units)
        spend_all_money(spend_money_matrix)
    else:
        spend_all_money(spend_money_matrix)
        move_all_units(actions, hexes_with_units)
    if len(SG.player1_provinces) == 0 or len(SG.player2_provinces) == 0:
        return 1
    return 0
