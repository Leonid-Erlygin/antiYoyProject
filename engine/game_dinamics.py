import sys
sys.path.insert(1, '/app')

from engine.state_generation import GameState



class MovePerformer:
    """
    Given Action probability distribution p calculates next game state
    """
    def __init__(self) -> None:
        pass
    def __call__(self, actions
    ):
        

class Game:
    def __init__(self, initial_game_state: GameState) -> None:


        
        self.game_state = initial_game_state

        
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
