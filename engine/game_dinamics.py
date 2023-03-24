import numpy as np


import sys

sys.path.insert(1, "/app")

from engine.state_generation import GameState


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

    def __init__(self) -> None:
        pass

    def __call__(
        self,
        game_state: GameState,
        activity_order,
        unit_movement_order,
        unit_move_actions,
        spend_money_matrix,
        hex_spend_order,
    ):
        # change current player after the end of move
        game_state.state_matrix = np.moveaxis(
            game_state.state_matrix,
            game_state.active_player_features,
            game_state.adversary_player_features,
        )
        game_state.change_active_player()
        return game_state


class Game:
    def __init__(self, initial_game_state: GameState) -> None:
        self.game_state = initial_game_state
        self.mover = MovePerformer()

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
            self.game_state = self.mover(
                self.game_state,
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
