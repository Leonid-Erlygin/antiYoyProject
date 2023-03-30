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
