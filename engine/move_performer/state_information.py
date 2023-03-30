from engine.state_generation import GameState
from collections import deque
import numpy as np

unit_food_map = {1: -2, 2: -6, 3: -18, 4: -36}
unit_cost_map = {1: 10, 2: 20, 3: 30, 4: 40}
action_unit_map = {0: 1, 1: 2, 2: 3, 5: 4}


def get_enemy_hex_defence(game_state: GameState, hexagon):
    """
    Возвращает силу, с которой защищается вражеский гексагон
    :param hexagon:
    :return:
    """
    power = 0

    for i in range(6):
        adj = game_state.getAdjacentHex(hexagon, i)
        if adj is None:
            continue
        if game_state.state[adj][game_state.adversary_player_dict["player_hexes"]] == 0:
            continue
        power = max(power, game_state.unit_type[adj], get_enemy_building(adj))
    return max(power, game_state.unit_type[hexagon], get_enemy_building(hexagon))


def get_enemy_building(game_state: GameState, hexagon):
    """
    Возращает силу защиты клетки зданием
    :param hexagon:
    :return:
    """
    # if state[hexagon][adversary_dict["tower1"]] == 1 and state[hexagon][adversary_dict["tower2"]] == 1:
    #     sys.exit("Две башни в одной клетке")

    if game_state.state_matrix[hexagon][game_state.adversary_player_dict["town"]] == 1:
        return 1
    if (
        game_state.state_matrix[hexagon][game_state.adversary_player_dict["tower1"]]
        == 1
    ):
        return 2
    if (
        game_state.state_matrix[hexagon][game_state.adversary_player_dict["tower2"]]
        == 1
    ):
        return 3
    return 0


def BFS_for_connectivity(game_state: GameState, hexagon):
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
    shiftX = compute_hex_by_layer(26, hexagon)[
        0
    ]  # задаёт нуль отсчёта по оси X( Нужно для отметок в массиве reached)
    shiftY = compute_hex_by_layer(0, hexagon)[1]  # задаёт нуль отсчёта по оси Y

    queue.append((hexagon, steps))
    reached[hexagon[0] - shiftX, hexagon[1] - shiftY] = True
    reachable_hexes.append(hexagon)
    while len(queue) != 0:
        next_hexagon, step = queue.popleft()
        if step != 0:
            for i in range(6):
                adj = game_state.getAdjacentHex(next_hexagon, i)
                if (
                    adj is not None
                    and reached[adj[0] - shiftX, adj[1] - shiftY] == 0
                    and game_state.state[adj][game_state.general_dict["black"]] != 1
                ):
                    if (
                        game_state.state[adj][
                            game_state.active_player_dict["player_hexes"]
                        ]
                        != 1
                    ):
                        reachable_hexes.append(adj)
                        reached[adj[0] - shiftX, adj[1] - shiftY] = True
                    else:
                        reached[adj[0] - shiftX, adj[1] - shiftY] = True
                        reachable_hexes.append(adj)
                        queue.append((adj, step - 1))

    return reachable_hexes


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
