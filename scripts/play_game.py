# Simulates game process for players with certain stategy

import hydra
from pathlib import Path
import sys

sys.path.insert(1, "/app")

from engine.game_dinamics import Game


def get_actions_distribution():
    pass


@hydra.main(
    config_path="/app/configs", config_name=Path(__file__).stem, version_base="1.2"
)
def play(cfg):
    # initialize random game
    initial_game_state = hydra.utils.instantiate(cfg.game_state)
    initial_game_state.generate_random_game()

    out_image_path = Path(cfg.exp_dir) / "random_init_state.png"
    initial_game_state.draw_game(out_image_path)
    print(out_image_path)

    # game = Game(initial_game_state)


if __name__ == "__main__":
    play()
