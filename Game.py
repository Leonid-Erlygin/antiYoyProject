import numpy as np
import Game_Process as GP
import State_Geneneration as sg
import time


# Замечания:
# - Нужно штрафовать нейронку, если она выбирает невозможные, по правилам игры, варианты
# Баги:
# - Лажа с индесами провинций, нужно тщательно проверить как они изменяются и что вообще происходит при разрыве провинции
# - Есть скриншот, где не создался город, хотя в провинции есть 2 клетки
def make_n_moves(n):
    for i in range(n):
        print(i)
        # if i == 222:
        #     sg.drawGame()
        GP.make_move(i % 2, seed=i, step=i)
        # if sg.state[14, 7, 20] == 1 and sg.state[14, 7, 27]==0:
        #     break
    # sg.drawGame()


sg.generate_random_game()
start_time = time.time()

make_n_moves(7000)
# !!! Баг - одиночная клетка находится в провинции, хотя она должна быть сама по себе
# !!! Деньги и доход не правильно пересчитываются(возможно потеря при разрывах)
sg.drawGame()
elapsed_time = time.time() - start_time
print(elapsed_time)
