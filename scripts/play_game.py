# Simulates game process for players with certain stategy

import hydra
from pathlib import Path
import sys
sys.path.insert(1, '/app')


@hydra.main(config_path='/app/configs',
    config_name=Path(__file__).stem,
    version_base="1.2")
def play(cfg):

    # initialize random game
    game = hydra.utils.instantiate(cfg.game_state)
    game.generate_random_game()

    out_image_path = Path(cfg.exp_dir) / 'random_init_state.png'
    game.draw_game(out_image_path)
    print(out_image_path)
    
    

if __name__ == '__main__':
    play()