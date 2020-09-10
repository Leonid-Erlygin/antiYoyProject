import State_Geneneration as sg
import numpy as np
from collections import deque
import sys

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
    ((-2, 4), (-2, 4))  # i<61
]
player = 0
player_dead_hexes = []
adversary_dead_hexes = []
adversary = 0
player_provinces = {}
adversary_provinces = {}
player_ambar_cost = {}
adversary_ambar_cost = {}
player_dict = {}
adversary_dict = {}
unit_food_map = {1: -2, 2: -6, 3: -18, 4: -36}
unit_cost_map = {1: 10, 2: 20, 3: 30, 4: 40}
action_unit_map = {0: 1, 1: 2, 2: 3, 5: 4}
steps = 0


def compute_hex_by_layer(i, hexagon):
    """

    :param i: номер возможного гексагона, в который можно перейти из данного
    :param hexagon: гексагон, в котором находится юнит
    :return: гексагон, соответсвующий номеру
    """
    odd = hexagon[1] % 2 != 0
    if i < 5:
        return base_hexes[0][odd][0] + hexagon[0] + i - 0, hexagon[1] + base_hexes[0][odd][1]
    if i < 11:
        return base_hexes[1][odd][0] + hexagon[0] + i - 5, hexagon[1] + base_hexes[1][odd][1]
    if i < 18:
        return base_hexes[2][odd][0] + hexagon[0] + i - 11, hexagon[1] + base_hexes[2][odd][1]
    if i < 26:
        return base_hexes[3][odd][0] + hexagon[0] + i - 18, hexagon[1] + base_hexes[3][odd][1]
    if i < 35:
        return base_hexes[4][odd][0] + hexagon[0] + i - 26, hexagon[1] + base_hexes[4][odd][1]
    if i < 43:
        return base_hexes[5][odd][0] + hexagon[0] + i - 35, hexagon[1] + base_hexes[5][odd][1]
    if i < 50:
        return base_hexes[6][odd][0] + hexagon[0] + i - 43, hexagon[1] + base_hexes[6][odd][1]
    if i < 56:
        return base_hexes[7][odd][0] + hexagon[0] + i - 50, hexagon[1] + base_hexes[7][odd][1]
    if i < 61:
        return base_hexes[8][odd][0] + hexagon[0] + i - 56, hexagon[1] + base_hexes[8][odd][1]


hex_by_layer = {}


# для ускорения работы эту функцию можно использовать один раз для составления таблицы по которой
# можно вычислять координаты точке


def get_action_distribution():
    """
    Возвращает полное распределение вероятностей для хода из данного состояния. Данные здесь не
    нормализуются. Выдаются вероятности с каким-то распределением. Лишь во время семплирования действий
    возможна нормализация.
    :return:
    activity_order - порядок в котором выполняются группа действий: сначала ход всеми юнитами или
    сначала потратить все деньги
    actions - из данной клетки юнит может перейти в 61 другую(включая эту же). Для задания вероятностей
    переходов используется массив (board_width, board_height, 61)
    hexes_with_units - массив указывающий в каких гексагонах были юниты в начале хода(может изменяться
    по мере семплирования). Это список пар: гексагон и вероятность сходить из этой клетки
    spend_money_matrix - деньги в каждом гексагоне можно потратить 7-ю способами. Эта матрица задаёт
    вероятности соответсвующих трат. Так же есть вероятность ничего не тратить в этом гексагоне - восьмая
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
    state = sg.state

    for i in range(field_size):
        hexagon = i // sg.width, i % sg.width

        if state[hexagon][player_dict["player_hexes"]] == 0 or sg.unit_type[hexagon] == 0:
            unit_movement_order[i] = 0
            actions[hexagon][:] = 0  # обнуление всех слоёв возможных ходов
        else:
            hexes_with_units.append([hexagon, unit_movement_order[i]])
    # hexes_with_units = np.asarray(hexes_with_units)

    # после зануления невозможных вероятностей, перенормализуем вектор
    if len(hexes_with_units) != 0:
        if len(hexes_with_units) == 1:
            hexes_with_units[0][1] = 1
        else:
            sum0 = 0
            for i in range(len(hexes_with_units)):
                sum0 += hexes_with_units[i][1]
            for i in range(len(hexes_with_units)):
                hexes_with_units[i][1] /= sum0

    # Нормализация действий проходит по ходу семплирования порядка движения юнитов
    # Так как от порядка зависит возможность и не возможность последующих действий
    ######

    # генерация порядка траты денег
    hex_spend_order = np.zeros(field_size) + 1.0 / field_size
    mean1 = np.zeros(8)
    mean1[:] = 1 / 8
    spend_money_matrix = np.zeros((sg.height, sg.width, 8))
    spend_money_matrix[:, :] = mean1

    return activity_order, actions, hexes_with_units, spend_money_matrix, hex_spend_order


def BFS_for_connectivity(hexagon):
    """
    Получает все возможные гексагоны, доступные из данного. Включая серые и вражеские.
    Недоступные вражеские зануляются отдельно.
    :param hexagon: Гексагон, из которого начинается поиск
    :return: список достижимых гексагонов
    """
    steps = 4
    queue = deque()
    reachable_hexes = []
    reached = np.zeros((9, 9), bool)
    # 26-ой слой задаёт верхний гексагон в круге потенциально доступных гексагонов
    shiftX = compute_hex_by_layer(26, hexagon)[0]  # задаёт нуль отсчёта по оси X( Нужно для отметок в массиве reached)
    shiftY = compute_hex_by_layer(0, hexagon)[1]  # задаёт нуль отсчёта по оси Y

    queue.append((hexagon, steps))
    reached[hexagon[0] - shiftX, hexagon[1] - shiftY] = True
    reachable_hexes.append(hexagon)
    while len(queue) != 0:
        hexagon, step = queue.popleft()
        if step != 0:
            for i in range(6):
                adj = sg.getAdjacentHex(hexagon, i)
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


def normalise_the_probabilities_of_actions(move, hexagon):
    """
    принимает на вход массив из 61 одного возможного хода и возвращает нормализованный(занулены невозможные ходы и вектор перенормирован)
    Условия, при которых в гексагон перейти нельзя:
    1)Он является чёрным, в нём есть наш амбар или центр города. Нужно проверить защиту этой клетки.
    2)Рядом должна быть дружественная клетка, либо она сама дружественная
    3)Добраться до этого гексагона юнит может только по своим клеткам(нужно проверить есть ли путь)
    4)Если в целевом гексагоне есть дружественный юнит, нужно проверить возможность слияния.
    Если хотя бы одно из условий выше не выполнено, такой ход зануляется.
    :param move: распределение вероятностей его возможных ходов
    :param hexagon: гексагон, в котором стоит юнит
    :return: возвращает пару: нормализованный вектор действий и список возможных ходов
    """
    state = sg.state
    # Имеет смысл сделать поиск в ширину из данного гексагона и определить гексаноны, до которых есть путь.
    # определение тип юнита в клетке:
    unit_type = sg.unit_type[hexagon]
    # 1 - крестьянин
    # 2 - копейщик
    # 3 - воин
    # 4 - рыцарь
    active_moves = []
    reachable_hexes = set(BFS_for_connectivity(hexagon))

    for i in range(61):
        hex_to_go = compute_hex_by_layer(i,
                                         hexagon)  # МОЖНО УСКОРИТЬ ЕСЛИ ДЕЛАТЬ ПРОВЕРКУ НА ЧЕРНОТУ И НА ВЫПАДЕНИЕ ИЗ КАРТЫ
        if i == 30:
            continue  # случай, когда остаёмся на месте
        if hex_to_go not in reachable_hexes or (state[hex_to_go][player_dict["player_hexes"]] == 1
                                                and (state[hex_to_go][player_dict["ambar"]] == 1
                                                     or state[hex_to_go][player_dict["tower1"]] == 1
                                                     or state[hex_to_go][player_dict["tower2"]] == 1
                                                     or state[hex_to_go][player_dict["town"]] == 1)):
            move[i] = 0
            continue
        # далее проверка не стоит ли в целевой клетке наш юнит

        if state[hex_to_go][player_dict["player_hexes"]] == 1:
            friendly_unit = sg.unit_type[hex_to_go]
            if friendly_unit != 0 and unit_type + friendly_unit > 4:
                move[i] = 0
                continue

        # далее проверка защищённости, если клетка вражеская

        if state[hex_to_go][adversary_dict["player_hexes"]] == 1:
            if unit_type <= get_enemy_hex_defence(hex_to_go):
                move[i] = 0
                continue
        # последний случай, когда клетка серая и доступная - можно ходить
        active_moves.append(i)

    sum0 = move.sum()
    if sum0 != 0:
        return move[:] / sum0, active_moves
    else:
        move[30] = 1  # - вероятность остаться на месте равна 1
        active_moves.append(30)
        return move, active_moves


def get_enemy_hex_defence(hexagon):
    """
    Возвращает силу, с которой защищается вражеский гексагон
    :param hexagon:
    :return:
    """
    power = 0
    for i in range(6):
        adj = sg.getAdjacentHex(hexagon, i)
        if adj is None:
            continue
        power = max(power, sg.unit_type[adj], get_enemy_building(adj))
    return max(power, sg.unit_type[hexagon], get_enemy_building(hexagon))


def get_enemy_building(hexagon):
    """
    Возращает силу защиты клетки зданием
    :param hexagon:
    :return:
    """
    state = sg.state
    if state[hexagon][adversary_dict["town"]] == 1:
        return 1
    if state[hexagon][adversary_dict["tower1"]] == 1:
        return 2
    if state[hexagon][adversary_dict["tower2"]] == 1:
        return 3
    return 0


def change_money_in_province(province_index, new_money, pl):
    """
    Вызывается во время хода игрока(трата денег, рубка деревьев, доход в конце хода)
    :param pl: Игрок в чьей провинции происходит изменение
    :param new_money: Новое значение денег в провинции
    :param province_index: Номер провинции игрока, совершающего ход
    :return: Изменение слоя
    """
    if pl == player:
        for hexagon in player_provinces[province_index]:
            sg.state[hexagon][player_dict["money"]] = new_money
    else:
        for hexagon in adversary_provinces[province_index]:
            sg.state[hexagon][adversary_dict["money"]] = new_money


def change_income_in_province(province_index, new_income, pl):
    """
    Вызывается во время хода игрока(добавление клетки, построение нового юнита, построение башни, построение амбара)
    :param pl: Игрок в чьей провинции происходит изменение
    :param province_index: Номер провинции игрока, совершающего ход
    :param new_income: Новый доход провинции
    :return: Изменение слоя
    """
    if pl == player:
        for hexagon in player_provinces[province_index]:
            sg.state[hexagon][player_dict["income"]] = new_income
    else:
        for hexagon in adversary_provinces[province_index]:
            sg.state[hexagon][adversary_dict["income"]] = new_income


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
    for hexagon in new_province_list:
        sg.state[hexagon][player_dict["money"]] = sum_money
        sg.state[hexagon][player_dict["income"]] = sum_income
        sg.state[hexagon][player_dict["province_index"]] = min_index

    player_provinces[min_index] = new_province_list


def detect_province_by_hex_with_income(hexagon, pl, province_index):
    """
    Возвращает провинцию игрока pl, которой лежит hex и заменяет идекс провинции на province_index.
     Кроме того возвращает число амбаров в провинции. Использует BFS
    :param province_index:
    :param hexagon:
    :param pl:
    :
    :return: Список гексагонов провиннции, доход провинции. Также возвращает маркер, если есть центр провинции, и число амбаров
    """
    queue = deque()
    province_hexes = []
    reached = np.zeros((sg.height, sg.width), bool)
    queue.append(hexagon)
    province_hexes.append(hexagon)
    reached[hexagon] = True
    diction = None
    number_of_barns = 0
    has_town = False
    total_income = 0
    if pl == player:
        diction = player_dict
    else:
        diction = adversary_dict
    if province_index != 0:
        sg.state[hexagon][diction["province_index"]] = province_index
    while len(queue) != 0:
        hexagon = queue.popleft()
        # подсчёт расхода клетки:
        if sg.unit_type[hexagon] != 0:
            total_income += unit_food_map[sg.unit_type[hexagon]]
        else:
            if sg.state[hexagon][diction["tower1"]] == 1:
                total_income += - 1
            elif sg.state[hexagon][diction["tower2"]] == 1:
                total_income += -6
            elif sg.state[hexagon][diction["ambar"]] == 1:
                number_of_barns += 1
                total_income += 4
            elif sg.state[hexagon][sg.general_dict["pine"]] == 1 or sg.state[hexagon][sg.general_dict["palm"]] == 1:
                total_income += -1
            elif sg.state[hexagon][diction["town"]] == 1:
                has_town = True
                total_income += 1
        for i in range(6):
            adj = sg.getAdjacentHex(hexagon, i)
            if adj is not None and reached[adj] == False and sg.state[adj][diction["player_hexes"]] == 1:
                province_hexes.append(adj)
                if province_index != 0:
                    sg.state[adj][diction["province_index"]] = province_index
                queue.append(adj)
                reached[adj] = True

    total_income += len(province_hexes)
    return province_hexes, total_income, has_town, number_of_barns


def find_place_for_new_town(province):
    """
    Находит первое попавшееся свободное место для нового городского центра. На вход приходит провинция, в которой уже уничтожили гексагон с центром города
    :param province: Индекс провинции
    :return: Гексагон для нового центра
    """
    for hexagon in adversary_provinces[province]:
        if sg.unit_type[hexagon] != 0:
            continue
        if sg.state[hexagon][adversary_dict["tower1"]] == 0 and sg.state[hexagon][adversary_dict["tower2"]] == 0 and \
                sg.state[hexagon][adversary_dict["ambar"]] == 0 and sg.state[hexagon][sg.general_dict["pine"]] == 0 and \
                sg.state[hexagon][sg.general_dict["palm"]] == 0:
            return hexagon

    sys.exit("Error: no place for town")


def perform_one_unit_move(departure_hex, destination_hex, unit_type):
    """
    Перемещает дружественный юнит в соответсвующую клетку, изменяя при этом состояние игры.
    При этом считается, что шаг возможен.
    Также функция может использоваться при создании нового юнита и помещения его в destination_hex.
    Считаем также, что в изначальном гексагоне юнита уже нет.
    На что может повлиять перемещение юнита:
    1)Серая клетка станет дружественной. Если на клетке было дерево, то оно исчезнет.
    2)Юнит перейдёт на дружественную клетку и ничего не изменится, кроме его положения
    3)Юнит перейдёт на дружественную клетку и срубит дерево, тем самым добавив 3 монеты к деньгам провинции
     и учеличив её доход на единицу.
    4)При захвате серой или вражеской клетки возможно соединение нескольких провинций в одну,
     что приведёт к созданию одной провинции c суммарным доходом(плюс клетка, на которую перешёл юнит) и с суммарными деньгами.
     Если провинции не слились в любом случае нужно добавить новую клетку в список клеток провинции,
     из которой ходил юнит.
    При слиянии, итоговая провинция получает индекс равный минимуму из индексов, сливаемых провинций.
    5)Если была захвачена вражеская клетка, то нужно проверить не разоравлись ли провинции при потери клетки. Если это произошло применить соответвующие преобразования:
    a)Добавить новые провинции и задать их параметры в список player_provinces
    b)Изменить состояние игры в полях income, money, province_index
    6)В нашей клетке мог стоять наш юнит и нужно провести слияние с соответвующими преобразованиями
    :param departure_hex: гексагон из которого отправились в путь.(Когда юнита покупают и сразу ставят, это любой гексагон из исходной провинции)
    :param destination_hex: Целевой гексагон
    :param unit_type: Тип юнита
    :return: изменение глобальной переменной SG.state
    """
    state = sg.state
    unit = "unit" + str(unit_type)
    # 2,3)
    # if steps == 222:
    #     x= 1
    if state[destination_hex][player_dict["player_hexes"]] == 1:
        if state[destination_hex][sg.general_dict["palm"]] == 1 or state[destination_hex][sg.general_dict["pine"]] == 1:
            tree = sg.general_dict["palm"] if sg.general_dict["palm"] == 1 else sg.general_dict["pine"]
            state[destination_hex][tree] = 0
            state[destination_hex][player_dict[unit]] = 1
            sg.unit_type[destination_hex] = unit_type
            change_money_in_province(province_index=sg.state[destination_hex][player_dict["province_index"]],
                                     new_money=state[destination_hex][player_dict["money"]] + 3, pl=player)
            change_income_in_province(province_index=sg.state[destination_hex][player_dict["province_index"]],
                                      new_income=state[destination_hex][player_dict["income"]] + 1, pl=player)
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
                                          new_income=state[destination_hex][player_dict["income"]] + reduce_income,
                                          pl=player)
                sg.unit_type[destination_hex] += unit_type
            else:
                sg.unit_type[destination_hex] = unit_type
                state[destination_hex][player_dict[unit]] = 1
    # 1,4,5):
    else:
        # необходимо произвести слияние наших клеток если это необходимо:
        destination_hex_province = state[destination_hex][adversary_dict["province_index"]]

        adjacent_hexes = sg.get_adjacent_hexes(destination_hex)
        adjacent_provinces = []
        for hexagon in adjacent_hexes:
            # !!! Здесь может быть нулевой гексагон !!!
            if hexagon is not None:
                province = state[hexagon][player_dict["province_index"]]
            else:
                continue
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
            sg.drawGame()
            sys.exit("in perform_one_unit_move function: no adjacent provinces detected")

        state[destination_hex][player_dict[unit]] = 1


        # если переходим в серую клетку, то можно не проверять разбились ли провинции врага
        if state[destination_hex][sg.general_dict["gray"]] == 1:
            # уничтожаем пальму или ёлку
            state[destination_hex][sg.general_dict["pine"]] = 0
            state[destination_hex][sg.general_dict["palm"]] = 0
            state[destination_hex][sg.general_dict["gray"]] = 0

        else:
            if destination_hex_province == 0:
                sys.exit("Индекс вражеской провинции не задан")
            # переходим во вражескую клетку. Нужно учесть возможный разрыв провинций.
            # также необходимо полностью уничтожить содержимое клетки

            root_of_possible_new_province = []
            Ax = sg.get_adjacent_friendly_hexes(destination_hex, player)
            gray_direction = 0
            for i in range(6):
                adj = sg.getAdjacentHex(destination_hex, i)
                if adj not in Ax and adj is not None:
                    gray_direction = i
                    break
            has_near = False
            for i in range(6):
                adj = sg.getAdjacentHex(destination_hex, (gray_direction + i) % 6)
                if adj in Ax and not has_near:
                    root_of_possible_new_province.append(adj)
                    has_near = True
                if adj not in Ax:
                    has_near = False

            # Теперь нужно понять являются ли эти корни частями разных провинций или они связаны
            actual_roots = []
            new_detected = {}  # словарь, задающий отображение : корень провинции - список гексагонов
            state[destination_hex][adversary_dict["player_hexes"]] = 0
            state[destination_hex][adversary_dict["province_index"]] = 0
            state[destination_hex][adversary_dict["income"]] = 0
            if len(root_of_possible_new_province) > 1:

                ok_roots = []
                while len(root_of_possible_new_province) != 0:
                    root = root_of_possible_new_province.pop()
                    province_hexes, _, _, _ = detect_province_by_hex_with_income(root, adversary, 0)
                    new_detected[root] = province_hexes
                    for val in root_of_possible_new_province:
                        if val not in province_hexes:
                            ok_roots.append(val)
                    root_of_possible_new_province = ok_roots
                    ok_roots = []
                    actual_roots.append(root)
            else:
                actual_roots = root_of_possible_new_province
            # уничтожаем всё что есть в клетке и ставим туда нашего юнита

            province = destination_hex_province

            if len(actual_roots) == 1 or len(actual_roots) == 0:

                state[destination_hex][adversary_dict["money"]] = 0

                # ничего создавать не нужно, просто провинция потеряла клетку и её содержимое(нужно изменить доход, в зависимости от того что было потеряно)

                try:
                    adversary_provinces[province].remove(destination_hex)
                except ValueError:
                    sg.drawGame()
                    sys.exit()
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
                # из одной провинции появилось несколько. Нужно удалить данные о старой провинции:
                sg.drawGame()
                breakpoint()
                del adversary_provinces[province]
                del adversary_ambar_cost[province]

                # зачистка узлового гексагона:
                if sg.unit_type[destination_hex] != 0:
                    state[destination_hex][adversary_dict["unit" + str(sg.unit_type[destination_hex])]] = 0
                else:
                    state[destination_hex][adversary_dict["tower1"]] = 0
                    state[destination_hex][adversary_dict["tower2"]] = 0
                    state[destination_hex][adversary_dict["ambar"]] = 0
                    state[destination_hex][adversary_dict["town"]] = 0
                sg.unit_type[destination_hex] = unit_type
                length = len(actual_roots)
                # !!! деньги распределяются равномерно, что не соответсвует действительности, тем более
                # когда осталась одна клетка в провинции !!!
                new_money = state[destination_hex][adversary_dict["money"]] // length
                remainder = state[destination_hex][adversary_dict["money"]] % length
                new_money_list = [new_money for _ in range(length)]
                state[destination_hex][adversary_dict["money"]] = 0
                i = 0
                while remainder != 0:
                    new_money_list[i] += 1
                    remainder -= 1
                    i += 1
                    i %= length
                # после раскола нужно расположить центры новый провинций
                # новые провинции получают индексы следующие после максимального
                key_for_new_province = 0
                if len(adversary_provinces) != 0:
                    key_for_new_province = max(adversary_provinces.keys()) + 1
                else:
                    key_for_new_province = 1
                i = 0
                # sg.drawGame()

                for root in actual_roots:
                    # доход нужно пересчитать нужно пересчитать для каждой оторвавшейся провинции, так как отдельно он не известен
                    # также нужно прописать новый индекс провинции
                    pr, income, has_town, number_of_ambars = detect_province_by_hex_with_income(root, adversary,
                                                                                                key_for_new_province)
                    if len(pr) > 1:  # если отвалился один гексагон, его можно выкинуть
                        adversary_provinces[key_for_new_province] = pr
                        adversary_ambar_cost[key_for_new_province] = 12 + number_of_ambars * 2
                    else:
                        if sg.unit_type[pr[0]] == 0:
                            sg.state[pr[0]][adversary_dict["town"]] = 0
                            sg.state[pr[0]][adversary_dict["tower1"]] = 0
                            sg.state[pr[0]][adversary_dict["tower2"]] = 0
                            sg.state[pr[0]][adversary_dict["ambar"]] = 0
                        else:
                            adversary_dead_hexes.append(pr[0])  # для последующего убийства юнита в нём
                        continue

                    change_income_in_province(key_for_new_province, income, adversary)
                    change_money_in_province(key_for_new_province, new_money=new_money_list[i], pl=adversary)

                    if not has_town:
                        place = find_place_for_new_town(key_for_new_province)
                        state[place][adversary_dict["town"]] = 1
                    i += 1
                    key_for_new_province += 1


def move_all_units(actions, hexes_with_units):
    """
    Перемешает всех доступных юнитов

    :param actions: Матрица, где каждому гексагону сопоставляем 61-о число - вероятность перейти в определённое место
    :param hexes_with_units: гексагоны, в которых есть наши юниты. В этом списке пары - гексагон и вероятность его выбрать первым при обходе поля
    :return:
    """
    order = []
    # семплирование порядка ходов: на каждом ходе выбирается юнит пропорционально его вероятности
    # затем он удаляется из списка и из остальных снова можно выбирать следующего

    # здесь предполагается, что в течении хода юниты которые не двигались продолжат оставаться в своих клетках
    for i in range(len(hexes_with_units)):
        r = np.random.random()
        s = 0
        for hexagon in hexes_with_units:

            s += hexagon[1]
            if r < s:
                order.append(hexagon)
                hexes_with_units.remove(hexagon)
                if len(hexes_with_units) != 0:
                    sum0 = 0
                    for j in range(len(hexes_with_units)):
                        sum0 += hexes_with_units[j][1]
                    for j in range(len(hexes_with_units)):
                        hexes_with_units[j][1] /= sum0
                break

    # на каждой итерации делается ход с учетом предыдущих итераций

    for hexagon in order:
        actions[hexagon[0]], active_moves = normalise_the_probabilities_of_actions(actions[hexagon[0]], hexagon[0])

        r = np.random.random()
        s = 0
        move = None
        # семплирование возможного хода
        for i in range(len(active_moves)):
            s += actions[hexagon[0]][active_moves[i]]
            if r < s:
                move = active_moves[i]
                break
        # making move
        if move is not None:
            if move == 30:
                continue  # случай, когда стоим на месте

            move_to_hex = compute_hex_by_layer(move, hexagon[0])
            unit = sg.unit_type[hexagon[0]]

            sg.state[hexagon[0]][unit] = 0
            sg.unit_type[hexagon[0]] = 0
            perform_one_unit_move(hexagon[0], move_to_hex, unit_type=unit)


def normalise_the_probabilities_of_spending(actions, hexagon):
    """
    # 0. unit 1 = 10
    # 1. unit 2 = 20
    # 2. unit 3 = 30
    # 3. small tower cost = 15
    # 4. big tower cost = 35
    # 5. unit 4 = 40
    # 6. ambar, цена зависит от текущего состояния и задаётся словарём 6
    # 7. ничего не делать

    # Есть тонкая важная проблема: что если на серый гексагон претендуют(находятся рядом) несколько провинций
    # будем считать что влюбом случает эти провинции объединятся и почти не важно кто их объединил
    # будем выбивать из двух возмножных акторов, того у кого больше сейчас денег, например
    :param actions: вероятности 8-ми описанных выше действий
    :param hexagon: гексагон, где ходим разместить покупку
    :return:
     - гексанон провинции, из которой мы тратим деньги. Если hex в нашей провинции, то возращаем его
     - отнормализованные действия
    """
    price_list = np.array([10, 15, 20, 30, 35, 40])
    # случай когда мы в уже в какой-то провинции:
    if sg.state[hexagon][player_dict["player_hexes"]] == 1:
        province = sg.state[hexagon][player_dict["province_index"]]
        # если провинция единичная: те гексагон формально раскрашен, но он один(не образует провинцию)
        # но ничего делать с ним нельзя(хотя бы потому что он не соединён с другими провинциями)
        if province not in player_provinces.keys():
            actions[:] = 0
            actions[7] = 1

            return hexagon, actions

        # Проверим не занята ли эта позиция: если занята зданием,
        # то возможно только 7-ое действие, а если занята юнитом то возможны другие
        if sg.state[hexagon][player_dict["tower2"]] == 1 or sg.state[hexagon][player_dict["town"]] == 1 or \
                sg.state[hexagon][player_dict["ambar"]] == 1 or sg.state[hexagon][player_dict["unit4"]] == 1:
            actions[:] = 0
            actions[7] = 1

            return hexagon, actions

        money = sg.state[hexagon][player_dict["money"]]
        # далее можно считать, что у нас, либо свободная клетка,
        # либо дерево, либо башня 1, либо один из трёх юнитов(5 вариантов)

        # на дерево нельзя строить никакие постройки!
        if sg.unit_type[hexagon] != 0:

            actions[3:7] = 0  # нельзя ставить строение на юнита
            accepted_units = np.array([1, 2, 3]) + sg.unit_type[hexagon] <= 4  # бинарная маска
            affordable_units = price_list[:3] <= money
            actions[:3] = actions[:3] * accepted_units * affordable_units
            # наложил бинарные маски на возможных юнитов и доступных юнитов
            if actions.sum() != 0:
                return hexagon, actions[:] / actions.sum()
            else:
                actions[7] = 1
                return hexagon, actions

        elif sg.state[hexagon][player_dict["tower1"]] == 1:
            if money < 35:
                return hexagon, actions
            else:
                actions[:4] = 0
                actions[5:7] = 0
                if actions.sum() != 0:
                    return hexagon, actions[:] / actions.sum()
                else:
                    actions[7] = 1
                    return hexagon, actions
        elif sg.state[hexagon][sg.general_dict["pine"]] == 1 or sg.state[hexagon][sg.general_dict["palm"]] == 1:
            # на дерево нельзя ставить никакие здания(четвёртого юнита потенциально можно)
            actions[3:5] = 0
            actions[6] = 0
            affordable_units = price_list[:3] <= money
            actions[:3] = actions[:3] * affordable_units
            if money < 40:
                actions[5] = 0
            if actions.sum() != 0:
                return hexagon, actions[:] / actions.sum()
            else:
                actions[7] = 1
                return hexagon, actions
        else:
            affordable_actions = price_list <= money
            actions[:6] = actions[:6] * affordable_actions
            # есть ли рядом амбар или городской центр?
            try:
                if player_ambar_cost[province] <= money:
                    near_ambar = False
                    for i in range(6):
                        adj = sg.getAdjacentHex(hexagon, i)
                        if adj is not None:
                            if sg.state[adj][player_dict["ambar"]] == 1 or sg.state[adj][player_dict["town"]] == 1:
                                near_ambar = True
                                break
                    if not near_ambar:
                        actions[6] = 0
                else:
                    actions[6] = 0
            except KeyError:
                sg.drawGame()
                sys.exit()
            # if player_ambar_cost[province] <= money:
            #     near_ambar = False
            #     for i in range(6):
            #         adj = sg.getAdjacentHex(hexagon, i)
            #         if adj is not None:
            #             if sg.state[adj][player_dict["ambar"]] == 1 or sg.state[adj][player_dict["town"]] == 1:
            #                 near_ambar = True
            #                 break
            #     if not near_ambar:
            #         actions[6] = 0
            # else:
            #     actions[6] = 0
            if actions.sum() != 0:
                return hexagon, actions[:] / actions.sum()
            else:
                actions[7] = 1
                return hexagon, actions
    else:
        # когда хотим потратить деньги во вражескую или в серую клетку
        adjacent_hexes = sg.get_adjacent_hexes(hexagon)
        adjacent_provinces = []  # смежный с hex гексагон, лежащий в другой провинции
        for hexagon in adjacent_hexes:
            province = sg.state[hexagon][player_dict["province_index"]]
            if province != 0 and hexagon not in adjacent_provinces:
                adjacent_provinces.append(hexagon)
        if len(adjacent_provinces) == 0:
            actions[:] = 0
            actions[7] = 1
            return hexagon, actions
        # далее нужно разобраться находится ли гексагон во вражеской провинции,
        # и действовать с учётом ближайших дружественных клеток

        # найдем провинцию от имени, которой действуем по принципу максимального числа денег
        max0 = -10000
        active_province_hex = None
        for hexagon in adjacent_provinces:
            if sg.state[hexagon][player_dict["money"]] > max0:
                active_province_hex = hexagon
                max0 = sg.state[hexagon][player_dict["money"]]
        money = sg.state[active_province_hex][player_dict["money"]]
        # здания ставить нельзя:
        actions[3:5] = 0
        actions[6] = 0
        affordable_units = price_list[:3] <= money
        if money < 40:
            actions[5] = 0  # юнита 4 нельзя

        if sg.state[hexagon][sg.general_dict["gray"]] == 1:
            # ставим любого доступного юнита
            actions[:3] = actions[:3] * affordable_units
        else:
            # вражеская клетка
            defence = get_enemy_hex_defence(hexagon)
            strong_enough = np.array([1, 2, 3]) >= defence
            actions[:3] = actions[:3] * affordable_units * strong_enough

        if actions.sum() != 0:
            return active_province_hex, actions[:] / actions.sum()
        else:
            actions[7] = 1
            return active_province_hex, actions


def spend_money_on_hex(hexagon, spend_hex, action):
    """
    Изменяет состояние игры.
    # 0. unit1
    # 1. unit2
    # 2. unit3
    # 3. tower1
    # 4. tower2
    # 5. unit4
    # 6. ambar
    # 7. ничего не делать
    :param hexagon: гексагон в котором тратят деньги
    :param action: действие, которое необходимо совершить
    :param spend_hex: гексагон от имени, которого идёт трата. Если hex лежить в дружеской провинции, то spend_hex == hex
    :return: изменение состояния игры
    """

    if action == 7:
        return
    elif action < 3 or action == 5:
        change_money_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                 new_money=sg.state[spend_hex][player_dict["money"]] - unit_cost_map[
                                     action_unit_map[action]], pl=player)
        change_income_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                  new_income=sg.state[spend_hex][player_dict["income"]] + unit_food_map[
                                      action_unit_map[action]], pl=player)
        perform_one_unit_move(departure_hex=spend_hex, destination_hex=hexagon, unit_type=action_unit_map[action])
    elif action == 3:
        change_money_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                 new_money=sg.state[spend_hex][player_dict["money"]] - 15, pl=player)
        change_income_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                  new_income=sg.state[spend_hex][player_dict["income"]] - 1, pl=player)
        sg.state[hexagon][player_dict["tower1"]] = 1
    elif action == 4:
        change_money_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                 new_money=sg.state[spend_hex][player_dict["money"]] - 35, pl=player)
        change_income_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                  new_income=sg.state[spend_hex][player_dict["income"]] - 6, pl=player)
        sg.state[hexagon][player_dict["tower2"]] = 1
    elif action == 6:
        change_money_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                 new_money=sg.state[spend_hex][player_dict["money"]] - player_ambar_cost[
                                     sg.state[spend_hex][player_dict["province_index"]]], pl=player)
        change_income_in_province(sg.state[spend_hex][player_dict["province_index"]],
                                  new_income=sg.state[spend_hex][player_dict["income"]] + 4, pl=player)
        player_ambar_cost[sg.state[spend_hex][player_dict["province_index"]]] += 2
    return


def spend_all_money(spend_money_matrix, hex_spend_order):
    """
    Тратит деньги во всех провинциях. Для каждого гескагона отдельно
    :param hex_spend_order: Порядок в котором обходятся гексагоны.
     Может ещё пригодиться, для короктировки нейро сети(чтобы не давала невозможные ответы)
    :param spend_money_matrix:
    Матрица, где каждому гексагону сопоставленно 8 чисел - 7 возможных трат денег и возможность ничего не делать

    :return: Изменение состояния игры
    """
    order = []
    not_black_hexes = []  # пары: допустимый гексагон и вероятность его выбора

    for i in range(len(hex_spend_order)):
        hexagon = i // sg.width, i % sg.width
        if sg.state[hexagon][sg.general_dict["black"]] == 1:
            hex_spend_order[i] = 0
            # нужно явно занулять такие вероятности, чтобы не выбирала ненулевыми вероятности для невозможных клеток
            continue
        not_black_hexes.append([hexagon, hex_spend_order[i]])

    for i in range(len(not_black_hexes)):
        r = np.random.random()
        s = 0
        for hexagon in not_black_hexes:
            s += hexagon[1]
            if r < s:
                order.append(hexagon[0])
                not_black_hexes.remove(hexagon)
                sum0 = 0
                # нормируем оставшиеся
                for hexag in not_black_hexes:
                    sum0 += hexag[1]

                for i in range(len(not_black_hexes)):
                    not_black_hexes[i][1] = not_black_hexes[i][1] / sum0
                break
    # order : каждый элемент - это гексагон
    for hexagon in order:
        spend_hex, spend_money_matrix[hexagon] = normalise_the_probabilities_of_spending(spend_money_matrix[hexagon],
                                                                                         hexagon)

        r = np.random.random()
        s = 0
        action = None

        # семплирование возможного действия
        for i in range(len(spend_money_matrix[hexagon])):
            s += spend_money_matrix[hexagon][i]
            # считаем, что если вероятность действия равна нулю, то его никогда не выбирут
            if r < s:
                action = i
                break
        if action is not None:
            spend_money_on_hex(hexagon, spend_hex, action)
        else:
            sys.exit("No accepted action in 'spend_all_money' function")


def after_move_changes():
    """
    Здесь происходят изменения согласно законам игры:
    1)После хода каждой провинции начисляется доход
    2)Голодные юниты умират
    3)Растёт лес
    :return:
    """


def make_move(move_player, seed, step):
    """
    Совершает ход игроком
    :param seed: Фиксирует случайность, для воспроизведения результатов
    :param move_player: 0 если первый игрок, 1 если второй
    :return: возвращает 1, если у одного из игроков закончились провинции. Иначе 0
    """
    global player_dict, adversary_dict, player_provinces, player_ambar_cost, adversary_ambar_cost, player, adversary_provinces, adversary, steps
    steps = step
    if move_player == 0:
        player = 0
        adversary = 1
        player_dict = sg.P1_dict
        adversary_dict = sg.P2_dict
        player_provinces = sg.player1_provinces
        adversary_provinces = sg.player2_provinces
        player_ambar_cost = sg.player1_province_ambar_cost
        adversary_ambar_cost = sg.player2_province_ambar_cost

    else:
        player = 1
        adversary = 0
        player_dict = sg.P2_dict
        adversary_dict = sg.P1_dict
        player_provinces = sg.player2_provinces
        adversary_provinces = sg.player1_provinces
        player_ambar_cost = sg.player2_province_ambar_cost
        adversary_ambar_cost = sg.player1_province_ambar_cost

    np.random.seed(seed)

    activity_order, actions, hexes_with_units, spend_money_matrix, hex_spend_order = get_action_distribution()
    activity = np.random.random() > activity_order[0]  # семплирование действия
    if activity == 0:
        move_all_units(actions, hexes_with_units)
        spend_all_money(spend_money_matrix, hex_spend_order)

    else:
        spend_all_money(spend_money_matrix, hex_spend_order)
        move_all_units(actions, hexes_with_units)

    if len(sg.player1_provinces) == 0 or len(sg.player2_provinces) == 0:
        return 1
    return 0
