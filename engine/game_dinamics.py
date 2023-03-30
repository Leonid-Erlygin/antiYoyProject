import numpy as np


import sys

sys.path.insert(1, "/app")

from engine.state_generation import GameState
from engine.move_performer.actions_before_and_after_players_move import (
    update_before_move,
)


def get_uniform_action_distribution(height, width, move_size):
    activity_order = [0.5, 0.5]
    field_size = height * width
    unit_movement_order = np.zeros(field_size) + 1.0 / field_size
    if move_size == 4:
        num_actions = 61
    if move_size == 2:
        num_actions = 1 + 6 + 12
    actions = np.zeros((height, width, num_actions))
    actions += 1 / num_actions

    spend_money_matrix = np.zeros((height, width, 8))
    spend_money_matrix += 1 / 8

    hex_spend_order = np.zeros(field_size) + 1.0 / field_size

    return (
        activity_order,
        unit_movement_order,
        actions,
        spend_money_matrix,
        hex_spend_order,
    )


class MovePerformer:
    """
    Given Action probability distribution p calculates next game state.
    After players moves state matrix S is transformed, so that first feature planes
    describe current player belongings.
    """

    def __init__(self, initial_game_state: GameState) -> None:
        r"""

        Args:
            initial_game_state: Состояние игры до начала хода текущего активного игрока
        """
        self.game_state = initial_game_state

    def make_move(
        self,
        activity_order: np.ndarray,
        unit_movement_order: np.ndarray,
        unit_move_actions: np.ndarray,
        spend_money_matrix: np.ndarray,
        hex_spend_order: np.ndarray,
    ) -> None:
        r"""
        Совершает ход активным игроком именяя self.game_state.
        Активный игрок - игрок чьи владения вписаны первыми в матрицу состояния

        Args:
            activity_order: порядок, в котором выполняются группа действий: сначала ход всеми юнитами или
            сначала потратить все деньги
            list: [p1, p2]

            unit_movement_order: порядок, в котором дружественные юниты делают свой ход
            array: (game_state.height, game_state.width)

            unit_move_actions: из данной клетки юнит может перейти в N других (включая эту же). Для задания вероятностей
            переходов используется. Число N - функция от максимальной длины шага юнита.
            Для длины шага 4 - N=61, для длины шага 2 - N=19
            array: (game_state.height, game_state.width, N)

            hex_spend_order: порядок, в котором будут обходиться клетки, в которых будут потрачены деньги.
            array: (game_state.height, game_state.width)

            spend_money_matrix: - деньги в каждом гексагоне можно потратить 7-ю способами. Эта матрица задаёт
            вероятности соответсвующих трат. Также есть вероятность ничего не тратить в этом гексагоне - восьмая
            array: (game_state.height, game_state.width, 8)

        Returns:
            None
        """
        update_before_move(self.game_state)

        # change current player after the end of move and transpose state matrix
        self.game_state.change_active_player()


class Game:
    def __init__(self, initial_game_state: GameState) -> None:
        self.game_state = initial_game_state
        self.mover = MovePerformer(initial_game_state)

    def play(self, number_of_moves):
        for _ in range(number_of_moves):
            (
                activity_order,
                unit_movement_order,
                unit_move_actions,
                spend_money_matrix,
                hex_spend_order,
            ) = get_uniform_action_distribution(
                self.game_state.height, self.game_state.width, self.game_state.move_size
            )
            self.mover.make_move(
                activity_order,
                unit_movement_order,
                unit_move_actions,
                spend_money_matrix,
                hex_spend_order,
            )

        # player = 0
        # adversary = 0
        # player_provinces = {}
        # adversary_provinces = {}
        # player_ambar_cost = {}
        # adversary_ambar_cost = {}
        # player_dict = {}
        # adversary_dict = {}
        # unit_food_map = {1: -2, 2: -6, 3: -18, 4: -36}
        # unit_cost_map = {1: 10, 2: 20, 3: 30, 4: 40}
        # action_unit_map = {0: 1, 1: 2, 2: 3, 5: 4}
        # steps = 0
        # rs = None
