import sys

sys.path.insert(1, "/app")

from engine.state_generation import GameState
from engine.move_performer.state_matrix_change_tools import (
    change_income_in_province,
    change_money_in_province,
)


def perform_one_unit_move(
    game_state: GameState, departure_hex, destination_hex, unit_type
):
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
    state = game_state.state_matrix
    player_dict = game_state.active_player_dict
    adversary_dict = game_state.adversary_player_dict
    player = game_state.active_player
    unit = "unit" + str(unit_type)
    # 2,3)

    if state[destination_hex][game_state.general_dict["graves"]] == 1:
        state[destination_hex][game_state.general_dict["graves"]] = 0
        game_state.graves_list.remove(destination_hex)

    if state[destination_hex][player_dict["player_hexes"]] == 1:
        if state[destination_hex][game_state.general_dict["pine"]] == 1:
            tree = game_state.general_dict["pine"]

            state[destination_hex][tree] = 0
            game_state.tree_list.remove(destination_hex)
            state[destination_hex][player_dict[unit]] = 1
            game_state.unit_type[destination_hex] = unit_type
            change_money_in_province(
                province_index=game_state.state[destination_hex][
                    player_dict["province_index"]
                ],
                new_money=state[destination_hex][player_dict["money"]] + 3,
                pl=player,
            )
            change_income_in_province(
                province_index=game_state.state[destination_hex][
                    player_dict["province_index"]
                ],
                new_income=state[destination_hex][player_dict["income"]] + 1,
                pl=player,
            )

        else:
            if game_state.unit_type[destination_hex] != 0:
                dest_unit = game_state.unit_type[destination_hex]
                state[destination_hex][
                    player_dict["unit" + str(dest_unit + unit_type)]
                ] = 1
                reduce_income = 0

                if unit_type == 1 and dest_unit == 1:
                    reduce_income = -2
                if (unit_type == 1 and dest_unit == 2) or (
                    unit_type == 2 and dest_unit == 1
                ):
                    reduce_income = -10
                if (unit_type == 1 and dest_unit == 3) or (
                    unit_type == 3 and dest_unit == 1
                ):
                    reduce_income = -16
                if unit_type == 2 and dest_unit == 2:
                    reduce_income = -24

                change_income_in_province(
                    state[destination_hex][player_dict["province_index"]],
                    new_income=state[destination_hex][player_dict["income"]]
                    + reduce_income,
                    pl=player,
                )
                game_state.unit_type[destination_hex] += unit_type

            else:
                game_state.unit_type[destination_hex] = unit_type
                state[destination_hex][player_dict[unit]] = 1
    # 1,4,5):
    else:
        if player == 0:
            game_state.p1_last_expanded_step = steps
        else:
            game_state.p2_last_expanded_step = steps
        # необходимо произвести слияние наших клеток если это необходимо:
        destination_hex_province = state[destination_hex][
            adversary_dict["province_index"]
        ]

        adjacent_hexes = game_state.get_adjacent_friendly_hexes(destination_hex, player)
        adjacent_provinces = []
        for hexagon in adjacent_hexes:
            province = state[hexagon][player_dict["province_index"]]

            if province not in adjacent_provinces:
                if province == 0:
                    # значит добавляем единичную клетку, для этого создадим фиктивную провинцию
                    new_key = max(player_provinces.keys()) + 1
                    province = new_key
                    player_provinces[new_key] = [hexagon]
                    player_ambar_cost[new_key] = 12
                    income = 1
                    if state[hexagon][game_state.general_dict["pine"]] == 1:
                        income = 0
                    state[hexagon][player_dict["income"]] = income

                adjacent_provinces.append(province)
        if len(adjacent_provinces) == 1:
            state[destination_hex][player_dict["player_hexes"]] = 1
            state[destination_hex][player_dict["money"]] = state[departure_hex][
                player_dict["money"]
            ]

            player_provinces[adjacent_provinces[0]] += [destination_hex]

            change_income_in_province(
                province_index=adjacent_provinces[0],
                new_income=state[departure_hex][player_dict["income"]] + 1,
                pl=player,
            )

            state[destination_hex][player_dict["province_index"]] = state[
                departure_hex
            ][player_dict["province_index"]]

        elif len(adjacent_provinces) > 1:
            merge_provinces(
                adjacent_provinces, destination_hex
            )  # слияние разных соседних провинций
        else:
            game_state.drawGame()
            sys.exit(
                "in perform_one_unit_move function: no adjacent provinces detected"
            )

        state[destination_hex][player_dict[unit]] = 1

        # если переходим в серую клетку, то можно не проверять разбились ли провинции врага
        if state[destination_hex][game_state.general_dict["gray"]] == 1:
            # уничтожаем пальму или ёлку
            if state[destination_hex][game_state.general_dict["pine"]] == 1:
                game_state.tree_list.remove(destination_hex)
                state[destination_hex][game_state.general_dict["pine"]] = 0
            state[destination_hex][game_state.general_dict["gray"]] = 0
            game_state.unit_type[destination_hex] = unit_type
        else:
            # переходим во вражескую клетку. Нужно учесть возможный разрыв провинций.
            # также необходимо полностью уничтожить содержимое клетки

            root_of_possible_new_province = []
            Ax = game_state.get_adjacent_friendly_hexes(destination_hex, not player)
            gray_direction = None
            for i in range(6):
                adj = game_state.getAdjacentHex(destination_hex, i)
                if adj not in Ax and adj is not None:
                    gray_direction = i
                    break
            has_near = False
            for i in range(6):
                adj = game_state.getAdjacentHex(
                    destination_hex, (gray_direction + i) % 6
                )
                if adj in Ax and not has_near:
                    root_of_possible_new_province.append(adj)
                    has_near = True
                if adj not in Ax:
                    has_near = False

            # Теперь нужно понять являются ли эти корни частями разных провинций или они связаны
            actual_roots = []
            new_detected = {}  # словарь, задающий отображение :
            # корень провинции - (список гексагонов,доход, имеется ли гор центр, число амбаров

            state[destination_hex][adversary_dict["player_hexes"]] = 0
            state[destination_hex][adversary_dict["province_index"]] = 0
            state[destination_hex][adversary_dict["income"]] = 0

            if len(root_of_possible_new_province) > 1:
                ok_roots = []
                while len(root_of_possible_new_province) != 0:
                    root = root_of_possible_new_province.pop()
                    (
                        province_hexes,
                        income,
                        has_town,
                        number_of_ambars,
                    ) = detect_province_by_hex_with_income(root, adversary, 0)
                    new_detected[root] = (
                        province_hexes,
                        income,
                        has_town,
                        number_of_ambars,
                    )
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

                # ничего создавать не нужно, просто провинция потеряла клетку и её содержимое(нужно изменить доход,
                # в зависимости от того что было потеряно)
                if len(actual_roots) != 0:
                    try:
                        adversary_provinces[province].remove(destination_hex)
                    except ValueError:
                        game_state.drawGame()
                        sys.exit()
                if len(actual_roots) != 0 and len(adversary_provinces[province]) == 1:
                    # значит провивинция состояла из двух клеток в одной из них был городской центр если центр был в
                    # destination_hex, то с последей точкой ничего не происходит, провинция просто исчезает если
                    # центр был в оставшейся клетке, то он уничтожается и на его месте вырастает дерево,
                    # провинция исчезает, клетка отаётся красной

                    # при уничтожении провинции всё должно исчезнуть, а юниты умереть, кроме может быть цвета
                    # последней клетки
                    remainder = adversary_provinces[province][0]
                    if state[destination_hex][adversary_dict["town"]] == 1:
                        state[destination_hex][adversary_dict["town"]] = 0

                        state[remainder][adversary_dict["ambar"]] = 0
                        state[remainder][adversary_dict["tower1"]] = 0
                        state[remainder][adversary_dict["tower2"]] = 0
                        state[remainder][adversary_dict["province_index"]] = 0
                        if game_state.unit_type[remainder] != 0:
                            game_state.dead_hexes.append(remainder)
                    else:
                        #  значит город в оставшейся клетке и там нужно вырастить дерево
                        state[remainder][adversary_dict["town"]] = 0

                        state[destination_hex][adversary_dict["ambar"]] = 0
                        state[destination_hex][adversary_dict["tower1"]] = 0
                        state[destination_hex][adversary_dict["tower2"]] = 0
                        state[destination_hex][game_state.general_dict["pine"]] = 0

                        adv_unit = game_state.unit_type[destination_hex]
                        if adv_unit != 0:
                            state[destination_hex][
                                adversary_dict["unit" + str(adv_unit)]
                            ] = 0
                        game_state.tree_list.append(remainder)
                        state[remainder][adversary_dict["province_index"]] = 0

                    state[remainder][adversary_dict["money"]] = 0
                    state[remainder][adversary_dict["income"]] = 0
                    del adversary_provinces[province]  # провинция исчезает
                    del adversary_ambar_cost[province]

                elif len(actual_roots) != 0:
                    # из вражеской провинции исчезла клетка и необходимо провести преобразования над провинцией
                    # если сломали городской центр нужно поставить новый в случайном свободном месте(возможно изменим)
                    adv_unit = game_state.unit_type[destination_hex]
                    gain = 0
                    if adv_unit != 0:
                        state[destination_hex][
                            adversary_dict["unit" + str(adv_unit)]
                        ] = 0

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
                            adversary_ambar_cost[province] -= 2
                            state[destination_hex][adversary_dict["ambar"]] = 0
                            gain = -4
                        elif (
                            state[destination_hex][game_state.general_dict["pine"]] == 1
                        ):
                            game_state.tree_list.remove(destination_hex)
                            state[destination_hex][game_state.general_dict["pine"]] = 0
                            gain = 1  # пальма запрещала доход  в этой клетке
                        elif state[destination_hex][adversary_dict["town"]] == 1:
                            state[destination_hex][adversary_dict["town"]] = 0
                            new_province_place = find_place_for_new_town(
                                province=province
                            )
                            state[new_province_place][adversary_dict["town"]] = 1
                    change_income_in_province(
                        province_index=province,
                        new_income=state[adversary_provinces[province][0]][
                            adversary_dict["income"]
                        ]
                        + gain
                        - 1,
                        pl=adversary,
                    )  # -1 за потерю клетки
                else:
                    if state[destination_hex][game_state.general_dict["pine"]] == 1:
                        game_state.tree_list.remove(destination_hex)
                        state[destination_hex][game_state.general_dict["pine"]] = 0

                game_state.unit_type[destination_hex] = unit_type

            else:
                # из одной провинции появилось несколько. Нужно удалить данные о старой провинции:

                del adversary_provinces[province]
                del adversary_ambar_cost[province]

                # зачистка узлового гексагона:
                if game_state.unit_type[destination_hex] != 0:
                    state[destination_hex][
                        adversary_dict[
                            "unit" + str(game_state.unit_type[destination_hex])
                        ]
                    ] = 0
                else:
                    state[destination_hex][adversary_dict["tower1"]] = 0
                    state[destination_hex][adversary_dict["tower2"]] = 0
                    state[destination_hex][adversary_dict["ambar"]] = 0
                    state[destination_hex][adversary_dict["town"]] = 0
                    if state[destination_hex][game_state.general_dict["pine"]] == 1:
                        game_state.tree_list.remove(destination_hex)
                        state[destination_hex][game_state.general_dict["pine"]] = 0
                    if state[destination_hex][game_state.general_dict["graves"]] == 1:
                        game_state.graves_list.remove(destination_hex)
                        state[destination_hex][game_state.general_dict["graves"]] = 0
                game_state.unit_type[destination_hex] = unit_type
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

                for root in actual_roots:
                    # доход нужно пересчитать для каждой оторвавшейся провинции, так как отдельно
                    # он не известен также нужно прописать новый индекс провинции
                    pr, income, has_town, number_of_ambars = new_detected[root]

                    if len(pr) > 1:  # если отвалился один гексагон, его можно выкинуть
                        adversary_provinces[key_for_new_province] = pr
                        # изменим номер провинции:
                        for hexagon in pr:
                            game_state.state[hexagon][
                                adversary_dict["province_index"]
                            ] = key_for_new_province
                        adversary_ambar_cost[key_for_new_province] = (
                            12 + number_of_ambars * 2
                        )
                    else:
                        state[pr[0]][adversary_dict["province_index"]] = 0
                        state[pr[0]][adversary_dict["money"]] = 0
                        if game_state.unit_type[pr[0]] == 0:
                            game_state.state[pr[0]][adversary_dict["town"]] = 0
                            game_state.state[pr[0]][adversary_dict["tower1"]] = 0
                            game_state.state[pr[0]][adversary_dict["tower2"]] = 0
                            game_state.state[pr[0]][adversary_dict["ambar"]] = 0
                            game_state.state[pr[0]][adversary_dict["income"]] = 0
                        else:
                            game_state.dead_hexes.append(
                                pr[0]
                            )  # для последующего убийства юнита в нём
                        continue

                    change_income_in_province(key_for_new_province, income, adversary)
                    change_money_in_province(
                        key_for_new_province, new_money=new_money_list[i], pl=adversary
                    )

                    if not has_town:
                        place = find_place_for_new_town(key_for_new_province)
                        state[place][adversary_dict["town"]] = 1
                    i += 1
                    key_for_new_province += 1
