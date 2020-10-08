import numpy as np
import Game_Process as GP
import State_Geneneration as sg
import time
import matplotlib.pyplot as plt


# Замечания:
# - Нужно штрафовать нейронку, если она выбирает невозможные, по правилам игры, варианты
# Баги:
# - Лажа с индесами провинций, нужно тщательно проверить как они изменяются и что вообще происходит при разрыве провинции
# - Есть скриншот, где не создался город, хотя в провинции есть 2 клетки

def make_n_moves(n):
    start_time = time.time()
    for i in range(n):
        print(i)
        # if i > 20:
        #     sg.drawGame()
        x = GP.make_move(i % 2, seed=i, step=i)
        if x == 1:
            print("Game over!")


sg.generate_random_game()
start_time = time.time()
make_n_moves(300)

# !!!
# !!! В игре старые могилы не сразу превращаются в деревья. Нужно реализовать метод превращения !!!
elapsed_time = time.time() - start_time
sg.drawGame()
print(elapsed_time)
