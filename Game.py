import numpy as np
import Game_Process as GP
import State_Geneneration as SG
import time

# Замечания:
# - Нужно штрафовать нейронку, если она выбирает невозможные, по правилам игры, варианты

SG.generate_random_game()
start_time = time.time()

GP.make_move(0,seed=0)
GP.make_move(1,seed=1)
GP.make_move(0,seed=2)
GP.make_move(1,seed=3)
GP.make_move(0,seed=0)
GP.make_move(1,seed=1)
GP.make_move(0,seed=2)
GP.make_move(1,seed=3)
SG.drawGame()

elapsed_time = time.time() - start_time
print(elapsed_time)
