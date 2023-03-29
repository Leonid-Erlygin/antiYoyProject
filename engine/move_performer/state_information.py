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
