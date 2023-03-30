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
