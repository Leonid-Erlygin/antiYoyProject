import sys

sys.path.insert(1, "/app")

from engine.state_generation import GameState


def change_money_in_province(game_state: GameState, province_index, new_money, pl):
    """
    Вызывается во время хода игрока(трата денег, рубка деревьев, доход в конце хода)
    :param pl: Игрок в чьей провинции происходит изменение
    :param new_money: Новое значение денег в провинции
    :param province_index: Номер провинции игрока, совершающего ход
    :return: Изменение слоя
    """
    if pl == game_state.active_player:
        for hexagon in game_state.active_player_provinces[province_index]:
            game_state.state_matrix[hexagon][
                game_state.active_player_dict["money"]
            ] = new_money
    else:
        for hexagon in game_state.adversary_player_provinces[province_index]:
            game_state.state_matrix[hexagon][
                game_state.adversary_player_dict["money"]
            ] = new_money


def change_income_in_province(game_state: GameState, province_index, new_income, pl):
    """
    Вызывается во время хода игрока(добавление клетки, построение нового юнита, построение башни, построение амбара)
    :param pl: Игрок в чьей провинции происходит изменение
    :param province_index: Номер провинции игрока, совершающего ход
    :param new_income: Новый доход провинции
    :return: Изменение слоя
    """
    if pl == game_state.active_player:
        for hexagon in game_state.active_player_provinces[province_index]:
            game_state.state_matrix[hexagon][
                game_state.active_player_dict["income"]
            ] = new_income
    else:
        for hexagon in game_state.adversary_player_provinces[province_index]:
            game_state.state_matrix[hexagon][
                game_state.adversary_player_dict["income"]
            ] = new_income
