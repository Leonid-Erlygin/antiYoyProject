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
