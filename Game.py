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
    for i in range(n):
        print(i)
        x = GP.make_move(i % 2, seed=i, step=i)
        if x == 1:
            print("Game over! Player {} wins!".format((i + 1) % 2))


sg.generate_random_game(1)
start_time = time.time()
make_n_moves(10000)

# !!! на ходе 9999 незанулённый амбар игрока 2
# !!! когда провинция игрока удоляется, необходимо удалять соответвующий элемент в player_province_ambar_cost
# !!! если игрок не сделал за 50 ходов ни одного хода юнитом, то он проигрывает


# !!! Нужно реализовать, рост деревьев после окончания хода.
# !!! Деньги при разделе провинций не должны делиться поровну !!!#
# !!! В игре старые могилы не сразу превращаются в деревья. Нужно реализовать метод превращения(или сразу?) !!!
elapsed_time = time.time() - start_time
sg.drawGame()
print(elapsed_time)
