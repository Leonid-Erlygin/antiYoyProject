import State_Geneneration as sg
import numpy as np
from collections import deque
import sys

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
adversary = 0
player_provinces = {}
adversary_provinces = {}
player_ambar_cost = {}
player_dict = {}
adversary_dict = {}
units = []
unit_food_map = {1: -2, 2: -6, 3: -18, 4: -36}


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
    field_size = sg.height * sg.width
    unit_movement_order = np.zeros(field_size) + 1.0 / field_size
    # нормальзация вектора ходов юнитов

    hexes_with_units = []

    # получим матрицу ходов для юнитов
    actions = np.zeros((sg.height, sg.width, 61))
    mean = np.zeros(61)
    mean[:] = 1 / 61
    actions[:, :] = mean
    # проверка наличия юнита в клетке
    for i in range(field_size):
        hex = i // sg.width, i % sg.width
        state = sg.state
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
    spend_money_matrix = np.zeros((sg.height, sg.width, 7))
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
                adj = sg.getAdjacentHex(hex, i)
                if adj is not None and reached[adj[0] - shiftX, adj[1] - shiftY] == 0 and sg.state[adj][
                    sg.general_dict["black"]] != 1:
                    if sg.state[adj][player_dict["player_hexes"]] != 1:
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
    state = sg.state
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
        if i == 30: continue  # случай, когда остаёмся на месте
        if hex_to_go not in reachable_hexes or (state[hex_to_go][player_dict["player_hexes"]] == 1
                                                and (state[hex_to_go][player_dict["ambar"]] == 1
                                                     or state[hex_to_go][player_dict["tower1"]] == 1
                                                     or state[hex_to_go][player_dict["tower2"]] == 1
                                                     or state[hex_to_go][player_dict["town"]] == 1)):
            move[i] = 0
            continue
        # далее проверка не стоит ли в целевой клетке наш юнит

        if state[hex_to_go][player_dict["player_hexes"]] == 1:
            frendly_unit = get_friendly_unit(hex_to_go)
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
        adj = sg.getAdjacentHex(hex, i)
        if adj is None: continue
        power = max(power, get_enemy_unit(adj), get_enemy_building(adj))
    return max(power, get_enemy_unit(hex), get_enemy_building(hex))


def get_enemy_building(hex):
    """
    Возращает силу защиты клетки зданием
    :param hex:
    :return:
    """
    state = sg.state
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
    state = sg.state
    if state[hex][adversary_dict["unit1"]] == 1: return 1
    if state[hex][adversary_dict["unit2"]] == 1: return 2
    if state[hex][adversary_dict["unit3"]] == 1: return 3
    if state[hex][adversary_dict["unit4"]] == 1: return 4
    return 0


def get_friendly_unit(hex):
    """
    Возвращает юнита из дружественной клетки.
    :param hex: гексагон в котором нужно найти юнита
    :return: Тип юнита в клетке. Если его там нет, возвращает 0
    """
    state = sg.state
    if state[hex][units[0]] == 1: return 1
    if state[hex][units[1]] == 1: return 2
    if state[hex][units[2]] == 1: return 3
    if state[hex][units[3]] == 1: return 4
    return None


def change_money_in_province(province_index, new_money, pl):
    """
    Вызывается во время хода игрока(трата денег, рубка деревьев, доход в конце хода)
    :param pl: Игрок в чьей провинции происходит изменение
    :param new_money: Новое значение денег в провинции
    :param province_index: Номер провинции игрока, совершающего ход
    :return: Изменение слоя
    """
    if pl == player:
        for hex in player_provinces[province_index]:
            sg.state[hex][player_dict["money"]] = new_money
    else:
        for hex in adversary_provinces[province_index]:
            sg.state[hex][adversary_dict["money"]] = new_money


def change_income_in_province(province_index, new_income, pl):
    """
    Вызывается во время хода игрока(добавление клетки, построение нового юнита, построение башни, построение амбара)
    :param pl: Игрок в чьей провинции происходит изменение
    :param province_index: Номер провинции игрока, совершающего ход
    :param new_income: Новый доход провинции
    :return: Изменение слоя
    """
    if pl == player:
        for hex in player_provinces[province_index]:
            sg.state[hex][player_dict["income"]] = new_income
    else:
        for hex in adversary_provinces[province_index]:
            sg.state[hex][adversary_dict["income"]] = new_income


def merge_provinces(provinces_to_merge, junction_hex):
    """
    Сливает по всем правилам провинции в одну:
    - Индекс итоговой провинции - минимум из индексов
    - Необходимо задать доход и деньги итоговой провинции в матрице состояний
    - Удалить старые провинции из словаря
    - Добавить новую провинцию в словарь
    :param junction_hex: Гексагон, который привёл к слиянию
    :param provinces_to_merge:
    :return: изменяет словари и состояние игры
    """
    min_index = min(provinces_to_merge)
    sum_money = 0
    sum_income = 0
    new_province_list = []
    for province in provinces_to_merge:
        sample_hex = player_provinces[province][0]
        sum_money += sg.state[sample_hex][player_dict["money"]]
        sum_income += sg.state[sample_hex][player_dict["income"]]
        new_province_list += player_provinces[province]
        player_provinces.pop(province)
    sum_income += 1  # так как добавляется ещё и узловой гексагон
    new_province_list += [junction_hex]
    sg.state[junction_hex][player_dict["player_hexes"]] = 1
    for hex in new_province_list:
        sg.state[hex][player_dict["money"]] = sum_money
        sg.state[hex][player_dict["income"]] = sum_income
        sg.state[hex][player_dict["province_index"]] = min_index

    player_provinces[min_index] = new_province_list


def detect_province_by_hex_with_income(hex, pl):
    """
    Возвращает провинцию игрока pl, которой лежит hex. Использует BFS
    :param hex:
    :param pl:
    :return: Список гексагонов провиннции, доход провинции. Также возвращает маркер, если есть центр провинции
    """
    queue = deque()
    province_hexes = []
    reached = np.zeros((sg.width, sg.height), bool)
    queue.append(hex)
    reached[hex] = True
    province_hexes.append(hex)
    dict = None
    has_town = False
    total_income = 0
    if pl == player:
        dict = player_dict
    else:
        dict = adversary_dict
    while len(queue) != 0:
        hex = queue.popleft()
        # подсчёт расхода клетки:
        if sg.unit_type[hex] != 0:
            total_income += unit_food_map[sg.unit_type[hex]]
        else:
            if sg.state[hex][dict["tower1"]] == 1:
                total_income += - 1
            elif sg.state[hex][dict["tower2"]] == 1:
                total_income += -6
            elif sg.state[hex][dict["ambar"]] == 1:
                total_income += 4
            elif sg.state[hex][sg.general_dict["pine"]] == 1 or sg.state[hex][sg.general_dict["palm"]] == 1:
                total_income += -1
            elif sg.state[hex][dict["town"]] == 1:
                has_town = True
        for i in range(6):
            adj = sg.getAdjacentHex(hex, i)
            if adj is not None and reached[adj] == False and sg.state[adj][dict["player_hexes"]] == 1:
                province_hexes.append(adj)
                reached[adj] = True

    total_income += len(province_hexes)
    return province_hexes, total_income, has_town


def find_place_for_new_town(province):
    """
    Находит первое попавшееся свободное место для нового городского центра. На вход приходит провнция в которой уже уничтожили гексагон с центром города
    :param province: Индекс провинции
    :return: Гексагон для нового центра
    """
    for hex in adversary_provinces[province]:
        if sg.unit_type[hex] != 0: continue
        if sg.state[hex][adversary_dict["tower1"]] == 0 and sg.state[hex][adversary_dict["tower2"]] and \
                sg.state[hex][adversary_dict["ambar"]] == 0 and sg.state[hex][sg.general_dict["pine"]] == 0 and \
                sg.state[hex][sg.general_dict["palm"]] == 0:
            return hex

    sys.exit("Error: no place for town")


def perform_one_unit_move(departure_hex, destination_hex, unit_type):
    """
    Перемещает дружественный юнит в соответсвующую клетку, изменяя при этом состояние игры. При этом считается, что шаг возможен.
    Также функция может использоваться при создании нового юнита и помещения его в destination_hex. Считаем также, что в изначальном гексагоне
    юнита уже нет.
    На что может повлиять перемещение юнита:
    1)Серая клетка станет дружественной. Если на клетке было дерево, то оно исчезнет.
    2)Юнит перейдёт на дружественную клетку и ничего не изменится, кроме его положения
    3)Юнит перейдёт на дружественную клетку и срубит дерево, тем самым добавив 3 монеты к деньгам провинции и учеличив её доход на единицу.
    4)При захвате серой или вражеской клетки возможно соединение нескольких провинций в одну, что приведёт к созданию одной провинции с
    суммарным доходом(плюс клетка, на которую перешёл юнит) и с суммарными деньгами. Если провинции не слились в любом случае нужно
    добавить новую клетку в список клеток провинции, из которой ходил юнит.
    При слиянии, итоговая провинция получает индекс равный минимуму из индексов, сливаемых провинций.
    5)Если была захвачена вражеская клетка, то нужно проверить не разоравлись ли провинции при потери клетки. Если это произошло применить соответвующие преобразования:
    a)Добавить новые провинции и задать их параметры в список player_provinces
    b)Изменить состояние игры в полях income, money, province_index
    6)В нашей клетке мог стоять наш юнит и нужно провести слияние с соответвующими преобразованиями
    :param departure_hex: гексагон из которого отправились в путь.(Когда юнита покупают и сразу ставят, это любой гексагон из исходной провинции)
    :param destination_hex: Целевой гексагон
    :param unit_type: Тип юнита
    :param unit_index: Его индекс в массиве состояний(in state)
    :return: изменение глобальной переменной SG.state
    """

    # 2,3)
    state = sg.state
    unit = "unit" + str(unit_type)
    if state[destination_hex][player_dict["player_hexes"]] == 1:
        if state[destination_hex][sg.general_dict["palm"]] == 1 or state[destination_hex][sg.general_dict["pine"]] == 1:
            tree = sg.general_dict["palm"] if sg.general_dict["palm"] == 1 else sg.general_dict["pine"]
            state[destination_hex][tree] = 0
            state[destination_hex][player_dict[unit]] = 1
            change_money_in_province(province_index=sg.state[destination_hex][player_dict["province_index"]],
                                     new_money=state[destination_hex][player_dict["money"]] + 3)
            change_income_in_province(province_index=sg.state[destination_hex][player_dict["province_index"]],
                                      new_income=state[destination_hex][player_dict["income"]] + 1)
        else:
            if sg.unit_type[destination_hex] != 0:
                dest_unit = sg.unit_type[destination_hex]
                state[destination_hex][player_dict["unit" + str(dest_unit + unit_type)]] = 1
                reduce_income = 0
                if unit_type == 1 and dest_unit == 1:
                    reduce_income = - 2
                if (unit_type == 1 and dest_unit == 2) or (unit_type == 2 and dest_unit == 1):
                    reduce_income = -10
                if (unit_type == 1 and dest_unit == 3) or (unit_type == 3 and dest_unit == 1):
                    reduce_income = -16
                if unit_type == 2 and dest_unit == 2:
                    reduce_income = -24
                change_income_in_province(state[destination_hex][player_dict["province_index"]],
                                          new_income=state[destination_hex][player_dict["income"]] + reduce_income)
                sg.unit_type[destination_hex] += unit_type


    # 1,4,5):
    else:
        # необходимо произвести слияние наших клеток если это необходимо:
        destination_hex_province = state[destination_hex][adversary_dict["province_index"]]
        adjacent_hexes = sg.get_adjacent_hexes(destination_hex)
        adjacent_provinces = []
        for hex in adjacent_hexes:
            province = state[hex][player_dict["province_index"]]
            if province != 0 and province not in adjacent_provinces:
                adjacent_provinces.append(province)
        if len(adjacent_provinces) == 1:
            state[destination_hex][player_dict["player_hexes"]] = 1
            state[destination_hex][player_dict["money"]] = state[departure_hex][player_dict["money"]]

            player_provinces[adjacent_provinces[0]] += [destination_hex]

            change_income_in_province(adjacent_provinces[0], state[departure_hex][player_dict["income"]] + 1, pl=player)

            state[destination_hex][player_dict["province_index"]] = state[departure_hex][
                player_dict["province_index"]]

        elif len(adjacent_provinces) > 1:
            merge_provinces(adjacent_provinces, destination_hex)  # слияние разных соседних провинций
        else:
            sys.exit("in perform_one_unit_move function: no adjacent provinces detected")
        state[destination_hex][player_dict[unit]] = 1
        sg.unit_type[destination_hex] = unit_type
        # если переходим в серую клетку, то можно не проверять разбились ли провинции врага
        if state[destination_hex][sg.general_dict["gray"]] == 1:
            # уничтожаем пальму или ёлку
            state[destination_hex][sg.general_dict["pine"]] = 0
            state[destination_hex][sg.general_dict["palm"]] = 0
            state[destination_hex][sg.general_dict["gray"]] = 0

        else:
            # переходим во вражескую клетку. Нужно учесть возможный разрыв провинций.
            # также необходимо полностью уничтожить содержимое клетки
            root_of_new_province = []
            Ax = sg.get_adjacent_friendly_hexes(destination_hex, player)
            # Ax - множество соседей destination_hex, принадлежащих противнику
            # Если сущ y в Ax: такой что Ay пересеч с Ax = пустое множество, то y - часть новой отдельной провинции
            for y in Ax:
                Ay = sg.get_adjacent_friendly_hexes(y, player)
                intersect = False
                for hex in Ay:
                    if hex in Ax:
                        intersect = True
                        break
                if not intersect:
                    root_of_new_province.append(y)
            # здесь также необходимо учесть случай, когда у провинции остаётся только одна клетка

            # уничтожаем всё что есть в клетке и ставим туда нашего юнита
            state[destination_hex][adversary_dict["player_hexes"]] = 0

            state[destination_hex][adversary_dict["income"]] = 0

            province = destination_hex_province

            state[destination_hex][adversary_dict["province_index"]] = 0
            state[destination_hex][player_dict["province_index"]] = state[departure_hex][player_dict["province_index"]]

            if len(root_of_new_province) == 1 or len(root_of_new_province) == 0:
                state[destination_hex][adversary_dict["money"]] = 0
                # ничего создавать не нужно, просто провинция потеряла клетку и её содержимое(нужно изменить доход, в зависимости от того что было потеряно)
                adversary_provinces[province].remove(destination_hex)
                if len(adversary_provinces[province]) == 1:
                    # значит провивинция состояла из двух клеток
                    # в одной из них был городской центр
                    # если центр был в destination_hex, то с последей точкой ничего не происходит, провинция просто исчезает
                    # если центр был в оставшейся клетке, то он уничтожается и на его месте вырастает дерево, провинция исчезает, клетка отаётся красной

                    # при уничтожении провинции всё должно исчезнуть, а юниты умереть, кроме может быть цвета последней клетки
                    remainder = adversary_provinces[province][0]
                    if state[destination_hex][adversary_dict["town"]] == 1:
                        state[destination_hex][adversary_dict["town"]] = 0
                        state[remainder][adversary_dict["ambar"]] = 0
                        state[remainder][adversary_dict["tower1"]] = 0
                        state[remainder][adversary_dict["tower2"]] = 0

                        if sg.unit_type[remainder] != 0:
                            remanded_adv_unit = "unit" + str(sg.unit_type[remainder])
                            state[remainder][adversary_dict[remanded_adv_unit]] = 0
                            state[remainder][sg.general_dict["grave"]] = 1
                            sg.unit_type[remainder] = 0
                    else:
                        #  значит город в оставшейся клетке и там нужно вырастить дерево
                        state[remainder][adversary_dict["town"]] = 0
                        state[remainder][sg.general_dict["pine"]] = 1
                    state[remainder][adversary_dict["money"]] = 0
                    state[remainder][adversary_dict["income"]] = 0
                    del adversary_provinces[province]  # провинция исчезает

                else:
                    # из вражеской провинции исчезла клетка и необходимо провести преобразования над провинцией
                    # если сломали городской центр нужно поставить новый в случайном свободном месте(возможно изменим)
                    adv_unit = sg.unit_type[destination_hex]
                    gain = 0
                    if adv_unit != 0:
                        state[destination_hex][adversary_dict["unit" + str(adv_unit)]] = 0

                        if adv_unit == 1:
                            gain = 2
                        elif adv_unit == 2:
                            gain = 6
                        elif adv_unit == 3:
                            gain = 18
                        elif adv_unit == 4:
                            gain = 36

                    else:
                        if state[destination_hex][adversary_dict["tower1"]] == 1:
                            state[destination_hex][adversary_dict["tower1"]] = 0
                            gain = 1
                        elif state[destination_hex][adversary_dict["tower2"]] == 1:
                            state[destination_hex][adversary_dict["tower2"]] = 0
                            gain = 6
                        elif state[destination_hex][adversary_dict["ambar"]] == 1:
                            state[destination_hex][adversary_dict["ambar"]] = 0
                            gain = -4
                        elif state[destination_hex][sg.general_dict["pine"]] == 1 or state[destination_hex][
                            sg.general_dict["palm"]] == 1:
                            state[destination_hex][sg.general_dict["pine"]] = 0
                            state[destination_hex][sg.general_dict["palm"]] = 0
                            gain = 1  # пальма запрещала доход  в этой клетке
                        elif state[destination_hex][adversary_dict["town"]] == 1:
                            state[destination_hex][adversary_dict["town"]] = 0
                            new_province_place = find_place_for_new_town(province=province)
                            state[new_province_place][adversary_dict["town"]] = 1
                    change_income_in_province(province_index=province, new_income=gain - 1,
                                              pl=adversary)  # -1 за потерю клетки
                sg.unit_type[destination_hex] = unit_type
            else:
                # из одной провинции появилось несколько:

                # зачистка узлового гексагона:
                if sg.unit_type[destination_hex] != 0:
                    state[destination_hex][adversary_dict["unit" + str(sg.unit_type[destination_hex])]] = 0
                else:
                    state[destination_hex][adversary_dict["tower1"]] = 0
                    state[destination_hex][adversary_dict["tower2"]] = 0
                    state[destination_hex][adversary_dict["ambar"]] = 0
                    state[destination_hex][adversary_dict["town"]] = 0
                sg.unit_type[destination_hex] = unit_type
                new_money = state[destination_hex][adversary_dict["money"]]//len(root_of_new_province)
                remainder = state[destination_hex][adversary_dict["money"]] % len(root_of_new_province)
                new_money_list = [new_money for i in range(len(root_of_new_province))]
                state[destination_hex][adversary_dict["money"]] = 0
                i = 0
                while remainder!=0:
                    new_money_list[i]+=1
                    remainder-=1
                    i+=1
                    i%=len(root_of_new_province)
                # после раскола нужно расположить центры новый провинций
                # новые провинции получают индексы следующие после максимального
                key_for_new_province = max(adversary_dict.keys()) + 1
                i = 0
                for root in root_of_new_province:
                    # доход нужно пересчитать нужно пересчитать для каждой оторвавшейся провинции, так как отдельно он не известен
                    pr,income,has_town = detect_province_by_hex_with_income(root,adversary)
                    adversary_dict[key_for_new_province] = pr

                    change_income_in_province(key_for_new_province,income,adversary)
                    change_money_in_province(key_for_new_province,new_money=new_money_list[i],pl = adversary)

                    if not has_town:
                        place = find_place_for_new_town(key_for_new_province)
                        state[place][adversary_dict["town"]] = 1
                    i+=1



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
        if move is not None:
            if move == 30: continue  # случай, когда стоим на месте
            move_to_hex = compute_hex_by_layer(move, hex[0])
            if sg.state[hex[0]][units[0]] == 1:
                sg.state[hex[0]][units[0]] = 0  # юнит ушёл из гексагона
                perform_one_unit_move(hex[0],move_to_hex, unit_type=1)
            if sg.state[hex[0]][units[1]] == 1:
                sg.state[hex[0]][units[1]] = 0
                perform_one_unit_move(hex[0],move_to_hex, unit_type=2)
            if sg.state[hex[0]][units[2]] == 1:
                sg.state[hex[0]][units[2]] = 0
                perform_one_unit_move(hex[0],move_to_hex, unit_type=3)
            if sg.state[hex[0]][units[3]] == 1:
                sg.state[hex[0]][units[3]] = 0
                perform_one_unit_move(hex[0],move_to_hex, unit_type=4)


def near_provinces(hex):
    """

    :param hex: текущий гексагон
    :return: Возвращает три значения: Наличие провинции рядом, список пар соседнего гексагона и номера его провинции,
     все соседние гексагоны
    """
    near_hex = []
    adjacentHex = []
    for i in range(6):
        adj = sg.getAdjacentHex(hex, i)
        if adj is None: continue
        adjacentHex.append(hex)
        if sg.state[hex][player_dict["player_hexes"]] == 1:
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
    if sg.state[hex][player_dict["player_hexes"]] == 1:
        pronice = None
        for i in player_provinces:
            if hex in player_provinces[i]:
                pronice = i
        ##Проверим не занята ли эта позиция, а если занята юнитом то можно
        if sg.state[hex][player_dict["tower2"]] == 1 or \
                sg.state[hex][player_dict["ambar"]] == 1 or sg.state[hex][player_dict["unit4"]] == 1:
            actions[:] = 0
            return None, actions, active_actions

        money = sg.state[hex][player_dict["money"]]
        if sg.state[hex][player_dict["tower1"]] == 1:
            if money < 35:
                return None, actions, active_actions
            else:
                actions[:4] = 0
                actions[4] = 1
                actions[5:] = 0
                active_actions += [4]
                return (hex, pronice), actions, active_actions

        if sg.state[hex][player_dict["unit1"]] == 1 or sg.state[hex][player_dict["unit2"]] == 1 \
                or sg.state[hex][player_dict["unit3"]] == 1:
            actions[1] = 0
            actions[4:] = 0
        if money < 10:
            actions[:] = 0
            return None, actions, []
        isBarnNear = False
        if actions[6] != 0:
            adjacent_hexes = []
            for i in range(6):
                adj = sg.getAdjacentHex(hex, i)
                if adj is None: continue
                adjacent_hexes.append(hex)
            for hex0 in adjacent_hexes:
                if sg.state[hex0][player_dict["ambar"]] == 1: isBarnNear = True
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
                if sg.state[hex][player_dict["unit3"]] == 1:
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
                if sg.state[hex][player_dict["unit3"]] == 1:
                    actions[1:] = 0
                    active_actions += [0]
                if sg.state[hex][player_dict["unit2"]] == 1:
                    actions[3:] = 0
                    active_actions += [0, 2]
                if sg.state[hex][player_dict["unit1"]] == 1:
                    actions[4:] = 0
                    active_actions += [0, 2, 3]
            return (hex, pronice), actions[:] / actions[:].sum(), active_actions
        if money < 40:
            actions[5:6] = 0
            if actions[1] != 0:
                active_actions += [0, 1, 2, 3, 4]
            else:
                if sg.state[hex][player_dict["unit3"]] == 1:
                    actions[1:] = 0
                    active_actions += [0]
                if sg.state[hex][player_dict["unit2"]] == 1:
                    actions[3:] = 0
                    active_actions += [0, 2]
                if sg.state[hex][player_dict["unit1"]] == 1:
                    actions[4:] = 0
                    active_actions += [0, 2, 3]
            return (hex, pronice), actions[:] / actions[:].sum(), active_actions
        if actions[1] != 0:
            active_actions += [0, 1, 2, 3, 4, 5]
        else:
            if sg.state[hex][player_dict["unit3"]] == 1:
                actions[1:] = 0
                active_actions += [0]
            if sg.state[hex][player_dict["unit2"]] == 1:
                actions[3:] = 0
                active_actions += [0, 2]
            if sg.state[hex][player_dict["unit1"]] == 1:
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
        if sg.state[pair[0]][player_dict["money"]] > max:
            active_pair = pair
            max = sg.state[pair[0]][player_dict["money"]]
    money = sg.state[active_pair[0]][player_dict["money"]]
    actions[6] = 0  # амбар
    actions[1] = 0  # Башни
    actions[4] = 0
    isGray = sg.state[hex][sg.general_dict["gray"]] == 1
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
    global player_dict, adversary_dict, player_provinces, player_ambar_cost, player, units, adversary_provinces, adversary
    if move_player == 0:
        player = 0
        adversary = 1
        player_dict = sg.P1_dict
        adversary_dict = sg.P2_dict
        player_provinces = sg.player1_provinces
        adversary_provinces = sg.player2_provinces
        player_ambar_cost = sg.player1_province_ambar_cost
        units = compute_units()
    else:
        player = 1
        adversary = 0
        player_dict = sg.P2_dict
        adversary_dict = sg.P1_dict
        player_provinces = sg.player2_provinces
        adversary_provinces = sg.player1_provinces
        player_ambar_cost = sg.player2_province_ambar_cost
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
    if len(sg.player1_provinces) == 0 or len(sg.player2_provinces) == 0:
        return 1
    return 0
