from rl.mcts import Mcts

import Game_Process as gp
import state_geneneration as sg


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

    def simulate_games(self):
        """
        Here we simulate multiple games and add them to the game_data_poll
        :param game:
        :return:
        """
        game_data_poll = []
        for i in range(self.number_of_games):
            game_data_poll.append(self.simulate_one_game())
        return game_data_poll
