# %%
import Game_Process as gp
from state_geneneration import State

# Замечания:
# - Нужно штрафовать нейронку, если она выбирает невозможные, по правилам игры, варианты
# Баги:


def make_n_moves(game_state, n):
    for i in range(n):
        # print(i)
        x = gp.make_move(game_state, i % 2, step=i)
        if x == 1:
            print("Game over! Player {} wins with {} steps".format((i + 1) % 2, i))
            break


# def seed_range_test(low, high):
#     for i in np.arrange(low, high):
#         print("The seed is {}".format(i))
#         global rs
#         del rs
#         rs = sg.generate_random_game(i, need_to_draw=False)
#         make_n_moves(12000)
#         # sg.drawGame()
#         sg.state_zeroing()


def seed_test(seed):
    game_state = State(seed)

    game_state.generate_random_game(need_to_draw=False)

    # make_n_moves(game_state, 12000)

    game_state.drawGame()


if __name__ == "__main__":
    seed_test(1336)
# seed_range_test(574,600)

# exit()
# start_time = time.time()

# !!! Теперь игры заканчиваются довольно рано, поэтому нужно отдельно проверять игры с > 10000 ходами
# !!! Нужно реализовать, рост деревьев после окончания хода.
# !!! Деньги при разделе провинций не должны делиться поровну !!!#

# elapsed_time = time.time() - start_time
# sg.drawGame()
# breakpoint()
# print(elapsed_time)
# Useful hash tags:
# NOT EFFICIENT

# %%
