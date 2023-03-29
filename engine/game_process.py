import numpy as np
from collections import deque
import sys
from numpy.random import RandomState


player = 0
adversary = 0
player_provinces = {}
adversary_provinces = {}
player_ambar_cost = {}
adversary_ambar_cost = {}
player_dict = {}
adversary_dict = {}

steps = 0
rs = None  # type: RandomState


def zeroing_apparently_impossible_actions(unit_movement_order, actions):
    """
    Возвращает полное распределение вероятностей для хода из данного состояния. Данные здесь не
    нормализуются. Выдаются вероятности с каким-то распределением. Лишь во время семплирования действий
    возможна нормализация.
    :return:
    activity_order - порядок в котором выполняются группа действий: сначала ход всеми юнитами или
    сначала потратить все деньги
    actions - из данной клетки юнит может перейти в 61 другую(включая эту же). Для задания вероятностей
    переходов используется массив (board_height, board_width, 61)
    hexes_with_units - массив указывающий в каких гексагонах были юниты в начале хода(может изменяться
    по мере семплирования). Это список пар: гексагон и вероятность сходить из этой клетки
    spend_money_matrix - деньги в каждом гексагоне можно потратить 7-ю способами. Эта матрица задаёт
    вероятности соответсвующих трат. Также есть вероятность ничего не тратить в этом гексагоне - восьмая
    hex_spend_order - порядок в котором будут обходиться клетки, в которых будут потрачены деньги.
    """

    # сейчас сгенерирую случайно(равномерно для доступных действий)
    # activity_order = [0.5, 0.5]  # 0 - движение юнитов/1-трата денег
    # field_size = game_state.height * game_state.width
    # unit_movement_order = np.zeros(field_size) + 1.0 / field_size
    # нормализация вектора ходов юнитов

    hexes_with_units = []

    # получим матрицу ходов для юнитов
    # actions = np.zeros((game_state.height, game_state.width, 61))
    # mean = np.zeros(61)
    # mean[:] = 1 / 61
    # actions[:, :] = mean
    # проверка наличия юнита в клетке
    # state = game_state.state

    for i in range(game_state.height * game_state.width):
        hexagon = i // game_state.width, i % game_state.width

        if (
            game_state.state[hexagon][player_dict["player_hexes"]] == 0
            or game_state.unit_type[hexagon] == 0
        ):
            unit_movement_order[hexagon] = 0
            actions[hexagon][:] = 0  # обнуление всех слоёв возможных ходов
        else:
            hexes_with_units.append([hexagon, unit_movement_order[hexagon]])

    # после зануления невозможных вероятностей, перенормализуем вектор:

    # NOT EFFICIENT
    if len(hexes_with_units) != 0:
        if len(hexes_with_units) == 1:
            hexes_with_units[0][1] = 1
        else:
            # hexes_with_units[:][1] /= np.sum(hexes_with_units[:][1])

            sum0 = 0

            for i in range(len(hexes_with_units)):
                sum0 += hexes_with_units[i][1]
            for i in range(len(hexes_with_units)):
                hexes_with_units[i][1] /= sum0

    # Нормализация действий проходит по ходу семплирования порядка движения юнитов
    # Так как от порядка зависит возможность и не возможность последующих действий
    ######

    # генерация порядка траты денег
    # hex_spend_order = np.zeros(field_size) + 1.0 / field_size
    # mean1 = np.zeros(8)
    # mean1[:] = 1 / 8
    # spend_money_matrix = np.zeros((game_state.height, game_state.width, 8))
    # spend_money_matrix[:, :] = mean1

    return hexes_with_units


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
    state = game_state.state
    # Имеет смысл сделать поиск в ширину из данного гексагона и определить гексаноны, до которых есть путь.
    # определение тип юнита в клетке:
    unit_type = game_state.unit_type[hexagon]
    # 1 - крестьянин
    # 2 - копейщик
    # 3 - воин
    # 4 - рыцарь
    active_moves = []
    reachable_hexes = set(BFS_for_connectivity(hexagon))

    for i in range(61):
        hex_to_go = compute_hex_by_layer(
            i, hexagon
        )  # МОЖНО УСКОРИТЬ, ЕСЛИ ДЕЛАТЬ ПРОВЕРКУ НА ЧЕРНОТУ И НА ВЫПАДЕНИЕ ИЗ КАРТЫ
        # NOT EFFICIENT
        if i == 30:
            continue  # случай, когда остаёмся на месте
        if hex_to_go not in reachable_hexes or (
            state[hex_to_go][player_dict["player_hexes"]] == 1
            and (
                state[hex_to_go][player_dict["ambar"]] == 1
                or state[hex_to_go][player_dict["tower1"]] == 1
                or state[hex_to_go][player_dict["tower2"]] == 1
                or state[hex_to_go][player_dict["town"]] == 1
            )
        ):
            move[i] = 0
            continue
        # далее проверка не стоит ли в целевой клетке наш юнит

        if state[hex_to_go][player_dict["player_hexes"]] == 1:
            friendly_unit = game_state.unit_type[hex_to_go]
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


def merge_provinces(provinces_to_merge, junction_hex):
    """
    Сливает по всем правилам провинции в одну:
    - Индекс итоговой провинции - минимум из индексов
    - Необходимо задать доход и деньги итоговой провинции в матрице состояний
    - Удалить старые провинции из словаря
    - Удалить старую стоимость амбара из словаря
    - Добавить новую провинцию в словарь
    - Удалить старые городские центры
    :param junction_hex: Гексагон, который привёл к слиянию
    :param provinces_to_merge:
    :return: изменяет словари и состояние игры
    """
    min_index = min(provinces_to_merge)
    new_province_list = []
    sum_money = 0
    sum_income = 0
    number_of_ambars = 0
    # sg.drawGame()
    for province in provinces_to_merge:
        sample_hex = player_provinces[province][0]
        sum_money += game_state.state[sample_hex][player_dict["money"]]
        sum_income += game_state.state[sample_hex][player_dict["income"]]
        new_province_list += player_provinces[province]

        number_of_ambars += int((player_ambar_cost[province] - 12) / 2)

        del player_ambar_cost[province]
        player_provinces.pop(province)

    sum_income += 1  # так как добавляется ещё и узловой гексагон
    new_province_list += [junction_hex]
    game_state.state[junction_hex][player_dict["player_hexes"]] = 1
    first_town = True
    for hexagon in new_province_list:
        game_state.state[hexagon][player_dict["money"]] = sum_money
        game_state.state[hexagon][player_dict["income"]] = sum_income
        game_state.state[hexagon][player_dict["province_index"]] = min_index
        if game_state.state[hexagon][player_dict["town"]] == 1:
            if first_town:
                first_town = False
                continue
            else:
                game_state.state[hexagon][player_dict["town"]] = 0
    player_provinces[min_index] = new_province_list
    player_ambar_cost[min_index] = 12 + 2 * number_of_ambars


def detect_province_by_hex_with_income(hexagon, pl, province_index):
    """
    Возвращает провинцию игрока pl, которой лежит hex и заменяет индекс провинции на province_index.
     Кроме того возвращает число амбаров в провинции. Использует BFS
    :param province_index:
    :param hexagon:
    :param pl:
    :
    :return: Список гексагонов провиннции, доход провинции. Также возвращает маркер, если есть центр провинции, и число амбаров
    """
    queue = deque()
    province_hexes = []
    reached = np.zeros((game_state.height, game_state.width), bool)
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
        game_state.state[hexagon][diction["province_index"]] = province_index
    while len(queue) != 0:
        next_hexagon = queue.popleft()
        # подсчёт расхода клетки:
        if game_state.unit_type[next_hexagon] != 0:
            total_income += unit_food_map[game_state.unit_type[next_hexagon]]
        else:
            if game_state.state[next_hexagon][diction["tower1"]] == 1:
                total_income += -1
            elif game_state.state[next_hexagon][diction["tower2"]] == 1:
                total_income += -6
            elif game_state.state[next_hexagon][diction["ambar"]] == 1:
                number_of_barns += 1
                total_income += 4
            elif game_state.state[next_hexagon][game_state.general_dict["pine"]] == 1:
                total_income += -1
            elif game_state.state[next_hexagon][diction["town"]] == 1:
                has_town = True
        for i in range(6):
            adj = game_state.getAdjacentHex(next_hexagon, i)
            if (
                adj is not None
                and reached[adj] == False
                and game_state.state[adj][diction["player_hexes"]] == 1
            ):
                province_hexes.append(adj)
                if province_index != 0:
                    game_state.state[adj][diction["province_index"]] = province_index
                queue.append(adj)
                reached[adj] = True

    total_income += len(province_hexes)
    return province_hexes, total_income, has_town, number_of_barns


def find_place_for_new_town(province):
    """
    Находит первое попавшееся свободное место для нового городского центра.
    На вход приходит провинция, в которой уже уничтожили гексагон с центром города
    Если все места заняты, то возвращает любой гексагон с уничтожением объекта в нём находящемся, c изменением дохода
    :param province: Индекс провинции
    :return: Гексагон для нового центра
    """
    for hexagon in adversary_provinces[province]:
        if game_state.unit_type[hexagon] != 0:
            continue
        if (
            game_state.state[hexagon][adversary_dict["tower1"]] == 0
            and game_state.state[hexagon][adversary_dict["tower2"]] == 0
            and game_state.state[hexagon][adversary_dict["ambar"]] == 0
            and game_state.state[hexagon][game_state.general_dict["graves"]] == 0
            and game_state.state[hexagon][game_state.general_dict["pine"]] == 0
        ):
            return hexagon

    # выбараем случайный гексагон

    to_delete = None
    for hexagon in adversary_provinces[province]:
        if game_state.state[hexagon][adversary_dict["ambar"]] == 0:
            to_delete = hexagon
            break
    if to_delete is None:
        idx = rs.randint(0, len(adversary_provinces[province]))
        hexagon = adversary_provinces[province][idx]

        change_income_in_province(
            province_index=province,
            new_income=game_state.state[hexagon][adversary_dict["income"]] - 4,
            pl=adversary,
        )
        adversary_ambar_cost[province] -= 2
        game_state.state[hexagon][adversary_dict["ambar"]] = 0
        return hexagon
    gain = 0
    if game_state.unit_type[to_delete] != 0:
        gain = -unit_food_map[game_state.unit_type[to_delete]]
        unit = game_state.unit_type[to_delete]
        game_state.unit_type[to_delete] = 0
        game_state.state[to_delete][adversary_dict["unit" + str(unit)]] = 0
        if player == 0:
            game_state.p2_units_list.remove(to_delete)
        else:
            game_state.p1_units_list.remove(to_delete)
        game_state.units_list.remove(to_delete)
    elif game_state.state[to_delete][adversary_dict["tower1"]] == 1:
        gain = 1
        game_state.state[to_delete][adversary_dict["tower1"]] = 0
    elif game_state.state[to_delete][adversary_dict["tower2"]] == 1:
        game_state.state[to_delete][adversary_dict["tower2"]] = 0
        gain = 6
    elif game_state.state[to_delete][game_state.general_dict["graves"]] == 1:
        game_state.graves_list.remove(to_delete)
        game_state.state[to_delete][game_state.general_dict["graves"]] = 0
    elif game_state.state[to_delete][game_state.general_dict["pine"]] == 0:
        game_state.tree_list.remove(to_delete)
        gain = 1
        game_state.state[to_delete][game_state.general_dict["pine"]] = 0

    change_income_in_province(
        province_index=province,
        new_income=game_state.state[to_delete][adversary_dict["income"]] + gain,
        pl=adversary,
    )
    return to_delete


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

    # здесь предполагается, что в течении хода юниты, которые не двигались продолжат оставаться в своих клетках
    for i in range(len(hexes_with_units)):
        r = rs.random()
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
        actions[hexagon[0]], active_moves = normalise_the_probabilities_of_actions(
            actions[hexagon[0]], hexagon[0]
        )

        r = rs.random()
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
            move_to_hex = compute_hex_by_layer(move, hexagon[0])

            # if steps == 416 and move_to_hex == (12,11):
            #     sg.drawGame()
            #     breakpoint()

            # if hexagon[0] == move_to_hex and move != 30:
            #     sys.exit("Ошибка в обозначениях!")

            unit = game_state.unit_type[hexagon[0]]
            if hexagon[0] == move_to_hex:
                continue
            game_state.state[hexagon[0]][player_dict["unit" + str(unit)]] = 0
            game_state.unit_type[hexagon[0]] = 0

            has_already = game_state.unit_type[move_to_hex] > 0
            who_has_him = None
            if has_already:
                who_has_him = (
                    player
                    if game_state.state[move_to_hex][player_dict["player_hexes"]] == 1
                    else adversary
                )
            if player == 0:
                try:
                    game_state.p1_units_list.remove(hexagon[0])
                except ValueError:
                    game_state.drawGame()
                    breakpoint()
            else:
                try:
                    game_state.p2_units_list.remove(hexagon[0])
                except ValueError:
                    game_state.drawGame()
                    breakpoint()

            game_state.units_list.remove(hexagon[0])
            perform_one_unit_move(hexagon[0], move_to_hex, unit_type=unit)

            if not has_already:
                game_state.units_list.append(move_to_hex)
                if player == 0:
                    game_state.p1_units_list.append(move_to_hex)
                else:
                    game_state.p2_units_list.append(move_to_hex)
            else:
                if who_has_him == player:
                    return
                if who_has_him == adversary:
                    if adversary == 0:
                        game_state.p2_units_list.append(move_to_hex)
                        game_state.p1_units_list.remove(move_to_hex)
                    else:
                        game_state.p1_units_list.append(move_to_hex)
                        game_state.p2_units_list.remove(move_to_hex)


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
    # будем считать, что влюбом случает эти провинции объединятся и почти не важно кто их объединил
    # будем выбивать из двух возмножных акторов, того у кого больше сейчас денег, например
    :param actions: вероятности 8-ми описанных выше действий
    :param hexagon: гексагон, где ходим разместить покупку
    :return:
     - гексанон провинции, из которой мы тратим деньги. Если hexagon в нашей провинции, то возращаем его
     - отнормализованные действия
    """

    price_list = np.array([10, 20, 30, 15, 35, 40])

    # случай когда мы в уже в какой-то провинции:
    if game_state.state[hexagon][player_dict["player_hexes"]] == 1:
        province = game_state.state[hexagon][player_dict["province_index"]]
        # если провинция единичная: те гексагон формально раскрашен, но он один(не образует провинцию)
        # но ничего делать с ним нельзя(хотя бы потому что он не соединён с другими провинциями)
        if province not in player_provinces.keys():
            actions[:] = 0
            actions[7] = 1

            return hexagon, actions

        # Проверим не занята ли эта позиция: если занята зданием,
        # то возможно только 7-ое действие, а если занята юнитом то возможны другие
        if (
            game_state.state[hexagon][player_dict["tower2"]] == 1
            or game_state.state[hexagon][player_dict["town"]] == 1
            or game_state.state[hexagon][player_dict["ambar"]] == 1
            or game_state.state[hexagon][player_dict["unit4"]] == 1
        ):
            actions[:] = 0
            actions[7] = 1

            return hexagon, actions

        money = game_state.state[hexagon][player_dict["money"]]
        # далее можно считать, что у нас, либо свободная клетка,
        # либо дерево, либо башня 1, либо один из трёх юнитов(5 вариантов)

        # на дерево нельзя строить никакие постройки!
        if game_state.unit_type[hexagon] != 0:
            actions[3:7] = 0  # нельзя ставить строение на юнита
            accepted_units = (
                np.array([1, 2, 3]) + game_state.unit_type[hexagon] <= 4
            )  # бинарная маска
            affordable_units = price_list[:3] <= money
            actions[:3] = actions[:3] * accepted_units * affordable_units
            # наложил бинарные маски на возможных юнитов и доступных юнитов
            if actions.sum() != 0:
                return hexagon, actions[:] / actions.sum()
            else:
                actions[7] = 1
                return hexagon, actions

        elif game_state.state[hexagon][player_dict["tower1"]] == 1:
            if money < 35:
                actions[:] = 0
                actions[7] = 1
                return hexagon, actions
            else:
                actions[:4] = 0
                actions[5:7] = 0
                if actions.sum() != 0:
                    return hexagon, actions[:] / actions.sum()
                else:
                    actions[7] = 1
                    return hexagon, actions
        elif game_state.state[hexagon][game_state.general_dict["pine"]] == 1:
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
                        adj = game_state.getAdjacentHex(hexagon, i)
                        if adj is not None:
                            if (
                                game_state.state[adj][player_dict["ambar"]] == 1
                                or game_state.state[adj][player_dict["town"]] == 1
                            ):
                                near_ambar = True
                                break
                    if not near_ambar:
                        actions[6] = 0
                else:
                    actions[6] = 0
            except KeyError:
                game_state.drawGame()
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
        # NOT EFFICIENT
        # !!! Здесь можно опимизировать, избавившись от лишнего цикла
        # когда хотим потратить деньги во вражескую или в серую клетку
        adjacent_hexes = game_state.get_adjacent_hexes(hexagon)
        adjacent_provinces = []  # смежный с hex гексагон, лежащий в другой провинции
        for adj in adjacent_hexes:
            province = game_state.state[adj][player_dict["province_index"]]
            if province != 0 and adj not in adjacent_provinces:
                adjacent_provinces.append(adj)
        if len(adjacent_provinces) == 0:
            actions[:] = 0
            actions[7] = 1
            return hexagon, actions
        # далее нужно разобраться находится ли гексагон во вражеской провинции,
        # и действовать с учётом ближайших дружественных клеток

        # найдем провинцию от имени, которой действуем по принципу максимального числа денег
        max0 = -10000
        active_province_hex = None
        for adj in adjacent_provinces:
            if game_state.state[adj][player_dict["money"]] > max0:
                active_province_hex = adj
                max0 = game_state.state[adj][player_dict["money"]]
        money = game_state.state[active_province_hex][player_dict["money"]]
        # здания ставить нельзя:
        actions[3:5] = 0
        actions[6] = 0
        affordable_units = price_list[:3] <= money
        if money < 40:
            actions[5] = 0  # юнита 4 нельзя

        if game_state.state[hexagon][game_state.general_dict["gray"]] == 1:
            # ставим любого доступного юнита
            actions[:3] = actions[:3] * affordable_units
        else:
            # вражеская клетка
            defence = get_enemy_hex_defence(hexagon)
            strong_enough = np.array([1, 2, 3]) > defence
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
        has_already = game_state.unit_type[hexagon] > 0
        who_has_him = None
        if has_already:
            who_has_him = (
                player
                if game_state.state[hexagon][player_dict["player_hexes"]] == 1
                else adversary
            )
        change_money_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_money=game_state.state[spend_hex][player_dict["money"]]
            - unit_cost_map[action_unit_map[action]],
            pl=player,
        )
        change_income_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_income=game_state.state[spend_hex][player_dict["income"]]
            + unit_food_map[action_unit_map[action]],
            pl=player,
        )
        perform_one_unit_move(
            departure_hex=spend_hex,
            destination_hex=hexagon,
            unit_type=action_unit_map[action],
        )
        if not has_already:
            game_state.units_list.append(hexagon)
            if player == 0:
                game_state.p1_units_list.append(hexagon)
            else:
                game_state.p2_units_list.append(hexagon)
        else:
            if who_has_him == player:
                return
            if who_has_him == adversary:
                if adversary == 0:
                    game_state.p2_units_list.append(hexagon)
                    game_state.p1_units_list.remove(hexagon)
                else:
                    game_state.p1_units_list.append(hexagon)
                    game_state.p2_units_list.remove(hexagon)

    elif action == 3:
        change_money_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_money=game_state.state[spend_hex][player_dict["money"]] - 15,
            pl=player,
        )
        change_income_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_income=game_state.state[spend_hex][player_dict["income"]] - 1,
            pl=player,
        )
        game_state.state[hexagon][player_dict["tower1"]] = 1
    elif action == 4:
        gain = 0
        if game_state.state[hexagon][player_dict["tower1"]] != 0:
            gain = 1
            game_state.state[hexagon][player_dict["tower1"]] = 0
        change_money_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_money=game_state.state[spend_hex][player_dict["money"]] - 35,
            pl=player,
        )
        change_income_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_income=game_state.state[spend_hex][player_dict["income"]] - 6 + gain,
            pl=player,
        )
        game_state.state[hexagon][player_dict["tower2"]] = 1

    elif action == 6:
        change_money_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_money=game_state.state[spend_hex][player_dict["money"]]
            - player_ambar_cost[
                game_state.state[spend_hex][player_dict["province_index"]]
            ],
            pl=player,
        )
        change_income_in_province(
            game_state.state[spend_hex][player_dict["province_index"]],
            new_income=game_state.state[spend_hex][player_dict["income"]] + 4,
            pl=player,
        )
        player_ambar_cost[
            game_state.state[spend_hex][player_dict["province_index"]]
        ] += 2
        game_state.state[spend_hex][player_dict["ambar"]] = 1
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
        hexagon = i // game_state.width, i % game_state.width
        if game_state.state[hexagon][game_state.general_dict["black"]] == 1:
            hex_spend_order[i] = 0
            # нужно явно занулять такие вероятности, чтобы не выбирала ненулевыми вероятности для невозможных клеток
            continue
        not_black_hexes.append([hexagon, hex_spend_order[i]])

    for i in range(len(not_black_hexes)):
        r = rs.random()
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
    # prev = None
    for hexagon in order:
        (
            spend_hex,
            spend_money_matrix[hexagon],
        ) = normalise_the_probabilities_of_spending(
            spend_money_matrix[hexagon], hexagon
        )

        # if np.max(sg.state[:,:,sg.active_player_dict["income"]])!=17 and steps == 88:
        #     sg.drawGame()
        #     breakpoint()
        r = rs.random()
        s = 0
        action = None

        # семплирование возможного действия
        for i in range(len(spend_money_matrix[hexagon])):
            s += spend_money_matrix[hexagon][i]
            # считаем, что если вероятность действия равна нулю, то его никогда не выбирут
            if r < s:
                action = i
                break

        if action is not None and action != 7:
            spend_money_on_hex(hexagon, spend_hex, action)
        else:
            if action is None:
                sys.exit("No accepted action in 'spend_all_money' function")

        # prev = hexagon


def update_after_move():
    """
    Здесь происходят изменения согласно законам игры:
    1)Растёт лес
    :return:
    """
    # С вероятностью p каждое дерево заспавнит в случайном месте около себя ещё дерево
    p = 0.01
    p1_modified_province = []
    p2_modified_province = []
    for tree in game_state.tree_list:
        if rs.random() < p:
            valid_list = []
            for i in range(6):
                adj = game_state.getAdjacentHex(tree, i)
                if (
                    adj is not None
                    and not game_state.state[adj][game_state.general_dict["black"]]
                    and game_state.unit_type[adj] == 0
                ):
                    valid_list.append(adj)
            new_tree = valid_list[rs.randint(0, len(valid_list))]
            game_state.state[new_tree][game_state.general_dict["pine"]] = 1
            game_state.tree_list.append(new_tree)
            province1 = game_state.state[new_tree][
                game_state.active_player_dict["province_index"]
            ]
            province2 = game_state.state[new_tree][
                game_state.adversary_player_dict["province_index"]
            ]
            if province1 != 0:
                p1_modified_province.append(province1)
            elif province2 != 0:
                p2_modified_province.append(province2)
    p1_loss = {}
    p2_loss = {}
    for province in p1_modified_province:
        if province not in p1_loss:
            p1_loss[province] = 1
        else:
            p1_loss[province] += 1
    for province in p2_modified_province:
        if province not in p2_loss:
            p2_loss[province] = 1
        else:
            p2_loss[province] += 1
    for province in p1_loss.keys():
        change_income_in_province(
            province,
            game_state.state[game_state.player1_provinces[province][0]][
                game_state.active_player_dict["income"]
            ]
            - p1_loss[province],
            0,
        )
    for province in p2_loss.keys():
        change_income_in_province(
            province,
            game_state.state[game_state.player2_provinces[province][0]][
                game_state.adversary_player_dict["income"]
            ]
            - p2_loss[province],
            1,
        )


def calculate_income_to_check_program():
    """
    Вычисляет доход у обоих игроков
    :return:
    """
    province_income_1 = {}
    province_income_2 = {}
    for provinces, diction, province_income in zip(
        [game_state.player1_provinces, game_state.player2_provinces],
        [game_state.active_player_dict, game_state.adversary_player_dict],
        [province_income_1, province_income_2],
    ):
        for province in provinces.keys():
            income = 0
            for hexagon in provinces[province]:
                income += 1  # так как это наша клетка
                if (
                    game_state.state[hexagon][game_state.general_dict["pine"]] == 1
                    or game_state.state[hexagon][diction["tower1"]] == 1
                ):
                    income -= 1
                if game_state.unit_type[hexagon] != 0:
                    income += unit_food_map[game_state.unit_type[hexagon]]
                if game_state.state[hexagon][diction["tower2"]] == 1:
                    income -= 6
                if game_state.state[hexagon][diction["ambar"]] == 1:
                    income += 4
            province_income[province] = income

    return province_income_1, province_income_2


def game_consistency_check():
    # ASSERTIONS
    if (player_ambar_cost.keys() != player_provinces.keys()) or (
        adversary_ambar_cost.keys() != adversary_provinces.keys()
    ):
        game_state.drawGame()
        breakpoint()
        # проверяем, что юниты на правильных местах в массиве состояний:
    if player == 0:
        for hexagon in game_state.p1_units_list:
            if (
                game_state.state[hexagon][game_state.active_player_dict["player_hexes"]]
                == 0
            ):
                game_state.drawGame()
                breakpoint()
    else:
        for hexagon in game_state.p2_units_list:
            if (
                game_state.state[hexagon][
                    game_state.adversary_player_dict["player_hexes"]
                ]
                == 0
            ):
                game_state.drawGame()
                breakpoint()

    # abmar check
    ambar_num = 0
    for cost in player_ambar_cost.values():
        ambar_num += int((cost - 12) / 2)

    if np.sum(game_state.state[:, :, player_dict["ambar"]]) != ambar_num:
        game_state.drawGame()
        breakpoint()

    # income check

    x, y = calculate_income_to_check_program()
    p1_income = 0
    for province in game_state.player1_provinces.keys():
        hexagon = game_state.player1_provinces[province][0]
        p1_income += game_state.state[hexagon][game_state.active_player_dict["income"]]
    p2_income = 0
    for province in game_state.player2_provinces.keys():
        hexagon = game_state.player2_provinces[province][0]
        p2_income += game_state.state[hexagon][
            game_state.adversary_player_dict["income"]
        ]

    p1_real_income = np.sum(list(x.values()))
    p2_real_income = np.sum(list(y.values()))
    if p1_income != p1_real_income or p2_income != p2_real_income:
        game_state.drawGame()
        breakpoint()

    # unit check
    units_list = game_state.p1_units_list + game_state.p2_units_list
    if not set(units_list) == set(game_state.units_list):
        s = set(game_state.units_list) - set(units_list)
        game_state.drawGame()
        breakpoint()
    for unit_1 in game_state.p1_units_list:
        if (
            game_state.state[unit_1][game_state.active_player_dict["unit1"]] == 0
            and game_state.state[unit_1][game_state.active_player_dict["unit2"]] == 0
            and game_state.state[unit_1][game_state.active_player_dict["unit3"]] == 0
            and game_state.state[unit_1][game_state.active_player_dict["unit4"]] == 0
        ) or game_state.unit_type[unit_1] == 0:
            game_state.drawGame()
            breakpoint()
    for unit_2 in game_state.p2_units_list:
        if (
            game_state.state[unit_2][game_state.adversary_player_dict["unit1"]] == 0
            and game_state.state[unit_2][game_state.adversary_player_dict["unit2"]] == 0
            and game_state.state[unit_2][game_state.adversary_player_dict["unit3"]] == 0
            and game_state.state[unit_2][game_state.adversary_player_dict["unit4"]] == 0
        ) or game_state.unit_type[unit_2] == 0:
            game_state.drawGame()
            breakpoint()


def game_end_check():
    only_no_money_and_zero_income = True

    length = (
        len(game_state.p1_units_list) if player == 0 else len(game_state.p2_units_list)
    )
    if length != 0:
        only_no_money_and_zero_income = False
    else:
        for province in player_provinces.keys():
            if (
                game_state.state[player_provinces[province][0]][player_dict["money"]]
                != 0
                or game_state.state[player_provinces[province][0]][
                    player_dict["income"]
                ]
                > 0
            ):
                only_no_money_and_zero_income = False
    if (
        only_no_money_and_zero_income
        or len(game_state.player1_provinces) == 0
        or len(game_state.player2_provinces) == 0
        or (int((steps - game_state.p1_last_expanded_step)) == 500)
        or ((steps - game_state.p2_last_expanded_step) == 500)
    ):
        x, y = calculate_income_to_check_program()
        # sg.drawGame()
        # breakpoint()
        return 1


def init(game_state0, move_player, step):
    global game_state, player_dict, adversary_dict, player_provinces, player_ambar_cost, adversary_ambar_cost, player, adversary_provinces, adversary, steps, rs
    del rs
    game_state = game_state0
    rs = game_state.rs
    steps = step

    if move_player == 0:
        player = 0
        adversary = 1
        player_dict = game_state.active_player_dict
        adversary_dict = game_state.adversary_player_dict
        player_provinces = game_state.player1_provinces
        adversary_provinces = game_state.player2_provinces
        player_ambar_cost = game_state.player1_province_ambar_cost
        adversary_ambar_cost = game_state.player2_province_ambar_cost

    else:
        player = 1
        adversary = 0
        player_dict = game_state.adversary_player_dict
        adversary_dict = game_state.active_player_dict
        player_provinces = game_state.player2_provinces
        adversary_provinces = game_state.player1_provinces
        player_ambar_cost = game_state.player2_province_ambar_cost
        adversary_ambar_cost = game_state.player1_province_ambar_cost


def make_move(
    game_state0,
    move_player,
    step,
    activity_order,
    unit_movement_order,
    actions,
    spend_money_matrix,
    hex_spend_order,
):
    """
    Совершает ход игроком
    :param hex_spend_order: порядок, в котором будут обходиться клетки, в которых будут потрачены деньги.
    array: (game_state.height, game_state.width)
    :param spend_money_matrix: - деньги в каждом гексагоне можно потратить 7-ю способами. Эта матрица задаёт
    вероятности соответсвующих трат. Также есть вероятность ничего не тратить в этом гексагоне - восьмая
    array: (game_state.height, game_state.width, 8)
    :param actions: из данной клетки юнит может перейти в 61 другую (включая эту же). Для задания вероятностей
    переходов используется
    array: (game_state.height, game_state.width, 61)
    :param unit_movement_order: порядок, в котором дружественные юниты делают свой ход
    array: (game_state.height, game_state.width)
    :param activity_order: - порядок, в котором выполняются группа действий: сначала ход всеми юнитами или
    сначала потратить все деньги
    list: [p1, p2]
    :param step: Номер шага игры
    :param game_state0: Состояние игры на начало этого хода
    :param move_player: 0 если первый игрок, 1 если второй
    :return: возвращает 1, если у одного из игроков закончились провинции. Иначе 0
    """

    init(game_state0, move_player=move_player, step=step)

    if steps > 1:
        update_before_move()

    hexes_with_units = zeroing_apparently_impossible_actions(
        unit_movement_order, actions
    )

    activity = rs.random() > activity_order[0]  # семплирование действия
    # действия перед ходом игрока:

    if activity == 0:
        move_all_units(actions, hexes_with_units)
        spend_all_money(spend_money_matrix, hex_spend_order)
    else:
        spend_all_money(spend_money_matrix, hex_spend_order)
        move_all_units(actions, hexes_with_units)
    # update_after_move()
    # if steps == 5000:
    #     x, y = calculate_income_to_check_program()
    #     sg.drawGame()
    #     breakpoint()

    end = game_end_check()
    ##########
    # game_consistency_check()
    ##########
    if end == 1:
        return 1
    return 0
