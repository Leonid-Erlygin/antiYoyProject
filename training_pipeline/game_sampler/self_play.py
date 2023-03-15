from rl.mcts import Mcts

import Game_Process as gp
from state_geneneration import State


class SelfPlay:
    """
    Generates some games per iteration (~ 1000), and returns data about played games
    """

    def __init__(self, game_max_length, number_of_games, model):
        self.game_max_length = game_max_length
        self.number_of_games = number_of_games
        self.model = model

    def simulate_one_game(self):
        """
        Here we simulate game of self Play with current model
        :return:
        """
        seed = 3
        game_state = State(seed)
        x = 0
        z = 0
        game_data = []

        mcts = Mcts(1)
        for step in range(self.game_max_length):
            who_moves = step % 2
            (
                activity_order,
                unit_movement_order,
                actions,
                spend_money_matrix,
                hex_spend_order,
            ) = mcts.get_action_distribution()
            x = gp.make_move(
                game_state,
                who_moves,
                step,
                activity_order,
                unit_movement_order,
                actions,
                spend_money_matrix,
                hex_spend_order,
            )
            action_distribution = [
                activity_order,
                unit_movement_order,
                actions,
                spend_money_matrix,
                hex_spend_order,
            ]

            game_data.append([game_state.state, action_distribution])
            if x == 1:
                if (step + 1) % 2 == 0:
                    z = 1
                if (step + 1) % 2 == 1:
                    z = -1
                print(
                    "Game over! Player {} wins with {} steps".format(
                        (step + 1) % 2, step
                    )
                )
                break

        return game_data, z

    def simulate_games(self):
        """
        Here we simulate multiple games and add them to the game_data_poll
        :return:
        """
        game_data_poll = []
        for i in range(self.number_of_games):
            game_data, z = self.simulate_one_game()
            game_data_poll += game_data
        return game_data_poll
