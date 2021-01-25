import numpy as np
import Game_Process as GP
import State_Geneneration as sg
import time
import matplotlib.pyplot as plt
from numpy.random import MT19937
from numpy.random import RandomState, SeedSequence

# Замечания:
# - Нужно штрафовать нейронку, если она выбирает невозможные, по правилам игры, варианты
# Баги:
# Деньги пересчитываются не правильно
rs = RandomState(MT19937(SeedSequence(0)))


def make_n_moves(n):
    for i in range(n):
        # print(i)
        x = GP.make_move(i % 2, seed=i, step=i, rs0=rs)
        if x == 1:
            print("Game over! Player {} wins!, with {}, steps".format((i + 1) % 2, i))
            break


def seed_range_test(low, high):
    for i in np.arange(low, high):
        print("The seed is {}".format(i))
        global rs
        del rs
        rs = sg.generate_random_game(i, need_to_draw=False)
        make_n_moves(12000)
        # sg.drawGame()
        sg.state_zeroing()


def seed_test(seed):
    global rs
    del rs
    rs = sg.generate_random_game(seed, need_to_draw=False)
    make_n_moves(12000)
    sg.drawGame()
    sg.state_zeroing()


seed_test(300)
# seed_range_test(150,200)

# exit()
# start_time = time.time()

# !!! Нужно реализовать, рост деревьев после окончания хода.
# !!! Деньги при разделе провинций не должны делиться поровну !!!#

# elapsed_time = time.time() - start_time
# sg.drawGame()
# breakpoint()
# print(elapsed_time)
# Usefull hash tags:
# NOT EFFICIENT
