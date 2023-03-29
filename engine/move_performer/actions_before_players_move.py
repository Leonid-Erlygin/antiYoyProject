import sys

sys.path.insert(1, "/app")

from engine.state_generation import GameState
from engine.move_performer.state_information import unit_food_map
from engine.move_performer.state_matrix_change_tools import (
    change_income_in_province,
    change_money_in_province,
)


def update_before_move(game_state: GameState):
    """
    Выполняет все действия перед началом хода конкретного игрока. Функция вызывается перед "move all units"
    - Смерть голодных юнитов
    - Добавление дохода от провинций
    - Могилы превращаются в деревья
    :return:
    """
    # после смерти юнитов доход растёт и деньги добавляются по новому счёту
    province_casualties = []
    new_graves = []
    null_provinces = (
        []
    )  # провинции где произошло обнуление. В этом случае доход не добавляется, а денег 0
    remove_list = []
    units_list = game_state.p1_units_list + game_state.p2_units_list

    # NOT EFFICIENT
    for unit_hex in units_list:
        if (
            game_state.state_matrix[unit_hex][
                game_state.active_player_dict["player_hexes"]
            ]
            == 0
            or game_state.state_matrix[unit_hex][
                game_state.active_player_dict["province_index"]
            ]
            == 0
        ):
            continue
        elif (
            game_state.state_matrix[unit_hex][game_state.active_player_dict["money"]]
            + game_state.state_matrix[unit_hex][game_state.active_player_dict["income"]]
            < 0
        ):
            change_money_in_province(
                game_state.state_matrix[unit_hex][
                    game_state.active_player_dict["province_index"]
                ],
                0,
                game_state.active_player,
            )
            null_provinces.append(
                game_state.state_matrix[unit_hex][
                    game_state.active_player_dict["province_index"]
                ]
            )
            province_casualties.append(
                (
                    game_state.state_matrix[unit_hex][
                        game_state.active_player_dict["province_index"]
                    ],
                    game_state.unit_type[unit_hex],
                )
            )
            # if steps == 998 and unit_hex == (12,3):
            #     sg.drawGame()
            #     breakpoint()
            game_state.state_matrix[unit_hex][
                game_state.active_player_dict[
                    "unit" + str(game_state.unit_type[unit_hex])
                ]
            ] = 0
            game_state.unit_type[unit_hex] = 0
            remove_list.append(unit_hex)
            game_state.state_matrix[unit_hex][game_state.general_dict["graves"]] = 1
            new_graves.append(unit_hex)
    # if steps == 191:
    #     sg.drawGame()
    #     breakpoint()
    game_state.p1_units_list = [
        hexagon for hexagon in game_state.p1_units_list if hexagon not in remove_list
    ]
    game_state.p2_units_list = [
        hexagon for hexagon in game_state.p2_units_list if hexagon not in remove_list
    ]
    game_state.units_list = [
        hexagon for hexagon in game_state.units_list if hexagon not in remove_list
    ]
    # убиваем юнитов, которые остались в одной клетке
    for hexagon in game_state.dead_hexes:
        game_state.state_matrix[hexagon][
            game_state.active_player_dict["unit" + str(game_state.unit_type[hexagon])]
        ] = 0

        game_state.units_list.remove(hexagon)

        if (
            game_state.state_matrix[hexagon][
                game_state.active_player_dict["player_hexes"]
            ]
            == 1
        ):
            game_state.p1_units_list.remove(hexagon)
        else:
            game_state.p2_units_list.remove(hexagon)
        game_state.state_matrix[hexagon][game_state.general_dict["graves"]] = 1
        new_graves.append(hexagon)
        game_state.unit_type[hexagon] = 0
    game_state.dead_hexes = []

    # посчитаем доход, который получит каждая провинция после смерти юнитов. Могила не снимает доход.
    province_gain = {}
    for province, unit_type in province_casualties:
        if province not in province_gain.keys():
            province_gain[province] = -unit_food_map[unit_type]
        else:
            province_gain[province] += -unit_food_map[unit_type]
    for province in province_gain.keys():
        change_income_in_province(
            province,
            game_state.state_matrix[game_state.active_player_provinces[province][0]][
                game_state.active_player_dict["income"]
            ]
            + province_gain[province],
            game_state.active_player,
        )

    # начисление дохода невымершим провинциям, если деньги стали отрицательными,
    # то ставим 0 и больше не вычитаем отрицательный доход из нуля:
    for province in game_state.active_player_provinces.keys():
        if province not in null_provinces:
            if (
                game_state.state_matrix[
                    game_state.active_player_provinces[province][0]
                ][game_state.active_player_dict["money"]]
                == 0
                and game_state.state_matrix[
                    game_state.active_player_provinces[province][0]
                ][game_state.active_player_dict["income"]]
                <= 0
            ):
                # Если в провинции нет денег и доход отрицальный: ничего не делать
                continue

            if (
                game_state.state_matrix[
                    game_state.active_player_provinces[province][0]
                ][game_state.active_player_dict["money"]]
                + game_state.state_matrix[
                    game_state.active_player_provinces[province][0]
                ][game_state.active_player_dict["income"]]
                < 0
            ):
                change_money_in_province(province, 0, game_state.active_player)
            else:
                change_money_in_province(
                    province,
                    game_state.state_matrix[
                        game_state.active_player_provinces[province][0]
                    ][game_state.active_player_dict["money"]]
                    + game_state.state_matrix[
                        game_state.active_player_provinces[province][0]
                    ][game_state.active_player_dict["income"]],
                    game_state.active_player,
                )

    # старые могилы превращаются в деревья
    graves_to_remove = []
    province_loss = {}  # потери каждой провинции из-за роста новых деревьев
    for grave in game_state.graves_list:
        grave_player = (
            0
            if game_state.state_matrix[grave][
                game_state.active_player_dict["player_hexes"]
            ]
            == 1
            else 1
        )
        if game_state.active_player == grave_player:
            game_state.state_matrix[grave][game_state.general_dict["graves"]] = 0
            graves_to_remove.append(grave)
            game_state.state_matrix[grave][game_state.general_dict["pine"]] = 1
            game_state.tree_list.append(grave)
            province = game_state.state_matrix[grave][
                game_state.active_player_dict["province_index"]
            ]
            if province in province_loss.keys():
                province_loss[province] += 1
            elif province != 0:
                province_loss[province] = 1

    game_state.graves_list = [
        grave for grave in game_state.graves_list if grave not in graves_to_remove
    ] + new_graves
    for province in province_loss.keys():
        change_income_in_province(
            province,
            game_state.state_matrix[game_state.active_player_provinces[province][0]][
                game_state.active_player_dict["income"]
            ]
            - province_loss[province],
            game_state.active_player,
        )
