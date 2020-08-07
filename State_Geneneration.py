import numpy as np

import matplotlib.pyplot as plt
from matplotlib import collections, transforms

S = 200  # площадь описывающего круга(необходимо для координатной системы)
r = (S / np.pi) ** 0.5
width = 14  # параметры поля, измеряемые в гексагонах
height = 22

state = np.zeros((height, width, 29), "uint8")
unit_type = np.zeros((height,width),"uint8") # вспомогательный массив, указывающий тип юнита находящегося в данной клетке
                                             # юнит либо у игрока 1, либо у игрока 2
P1_dict = {"unit1": 4, "unit2": 5, "unit3": 6, "unit4": 7, "player_hexes": 8, "tower1": 9, "tower2": 10, "ambar": 11,
           "town": 12, "income": 13, "money": 14, "province_index": 15}
general_dict = {"black": 0, "gray": 1, "palm": 2, "pine": 3,"graves": 28}
P2_dict = {"unit1": 16, "unit2": 17, "unit3": 18, "unit4": 19, "player_hexes": 20, "tower1": 21, "tower2": 22,
           "ambar": 23, "town": 24, "income": 25, "money": 26,"province_index": 27}
player1_provinces = {}
player2_provinces = {}

state[:, :, general_dict["black"]] = 1

player1_province_ambar_cost = {}
player2_province_ambar_cost = {}

activeHexes = []


def getAdjacentHex(hex, direction):
    if direction == 0:
        if hex[1] == 0:
            return None

        if hex[0] == 0 and hex[1] % 2 == 0:
            return None

        if hex[1] % 2 == 1:
            return hex[0], hex[1] - 1
        else:
            return hex[0] - 1, hex[1] - 1

    if direction == 1:
        if hex[0] == 0:
            return None
        return hex[0] - 1, hex[1]
    if direction == 2:
        if hex[1] == width - 1:
            return None
        if hex[0] == 0 and hex[1] % 2 == 0:
            return None
        if hex[1] % 2 == 1:
            return hex[0], hex[1] + 1
        else:
            return hex[0] - 1, hex[1] + 1
    if direction == 3:
        if hex[1] == width - 1:
            return None
        if hex[0] == height - 1 and hex[1] % 2 == 1:
            return None
        if hex[1] % 2 == 0:
            return hex[0], hex[1] + 1
        else:
            return hex[0] + 1, hex[1] + 1
    if direction == 4:
        if hex[0] == height - 1:
            return None
        return hex[0] + 1, hex[1]
    if direction == 5:
        if hex[1] == 0 or (hex[0] == height - 1 and hex[1] % 2 == 1):
            return None
        if hex[1] % 2 == 1:
            return hex[0] + 1, hex[1] - 1

def get_adjacent_hexes(hex):
    """
    Возвращает список прилегающих гексагонов
    :param hex: Гексагон, для которого ищем соседей
    :return:
    """
    adjacent = []
    for i in range(6):
        adj = getAdjacentHex(hex,i)
        if adj is not None:
            adjacent.append(adj)
    return adjacent
def get_adjacent_friendly_hexes(hex,player):
    """
    Возвращает список дружественных прилегающих гексагонов
    :param hex: Гексагон, для которого ищем соседей
    :param player: Игрок
    :return:
    """
    adjacent = []
    layer = P1_dict["player_hexes"] if player == 1 else P2_dict["player_hexes"]
    for i in range(6):
        adj = getAdjacentHex(hex, i)
        if adj is not None and state[adj][layer] == 1:
            adjacent.append(adj)
    return adjacent
def spawnIsland(startHex, size):
    global activeHexes
    global state
    gen = np.zeros((height, width), "bool")  # матрица которая будет указывать сгенерировали ли
    # что-то клетка или нет
    genPotential = np.zeros((height, width), "uint8")  # Число - потенциал генирации
    genPotential[startHex] = size
    propagationList = []
    propagationList.append(startHex)
    while len(propagationList) > 0:
        hex = propagationList.pop()
        gen[startHex] = 1

        if np.random.randint(low=0, high=size) > genPotential[hex]: continue
        x = state[hex][general_dict["gray"]] != 1
        if x: activeHexes.append(hex)
        state[hex][general_dict["gray"]] = 1  # клетка из чёрной становится серой
        state[hex][general_dict["black"]] = 0  # эта клетка больше не чёрная

        if genPotential[hex] == 0 or not x: continue

        for i in range(6):
            adjHex = getAdjacentHex(hex, i)
            if (not adjHex is None and not gen[adjHex] and propagationList.count(adjHex) == 0):
                genPotential[adjHex] = genPotential[hex] - 1
                propagationList.append(adjHex)


def computeCoordinates(hex):
    x = r * 3 ** 0.5 * hex[0] + r * ((1 - (-1) ** hex[1]) * 3 ** 0.5) / 4
    y = r * (3 / 2) * hex[1]
    return x, y


def getHexByPos(x, y):
    j = int((2 / (r * 3)) * y)
    i = int((x - r * ((1 - (-1) ** j) * 3 ** 0.5) / 4) / (r * 3 ** 0.5))
    if i < 0 or i > height - 1 or j < 0 or j > width - 1: return 0
    return i, j


def uniteIslandsWithRoads(centers):
    global activeHexes
    global state
    startPoint = computeCoordinates(centers[0])
    endPoint = computeCoordinates(centers[1])
    distance = ((startPoint[0] - endPoint[0]) ** 2 + (startPoint[1] - endPoint[1]) ** 2) ** 0.5
    angle = np.angle([complex(endPoint[0] - startPoint[0], endPoint[1] - startPoint[1])])
    delta = r / 2
    n = (int)(distance / delta)
    prev = (-1, -1)
    for i in range(n):
        currentX = startPoint[0] + delta * i * np.cos(angle)
        currentY = startPoint[1] + delta * i * np.sin(angle)
        hex = getHexByPos(currentX, currentY)
        # spawnIsland(hex, 2)
        if hex != prev:
            spawnIsland(hex, 2)
            prev = hex


def getRandomHexInsideBounds():
    return np.random.randint(height), np.random.randint(width)


def isNearWater(hex):
    for i in range(6):
        adj = getAdjacentHex(hex, i)
        if adj is None:
            continue
        if state[adj][general_dict["black"]] == 1:
            return True
    return False


def spawnTree(hex):
    global activeHexes
    global state
    if isNearWater(hex):
        state[hex][general_dict["palm"]] = 1  # Добавил пальму
    else:
        state[hex][general_dict["pine"]] = 1  # Добавил ёлку


def addTrees():
    for hex in activeHexes:
        if np.random.rand() < 0.1: spawnTree(hex)


def findGoodPlaceForNewProvince(fraction):
    global activeHexes
    global state
    if (fraction == 0):  # Возвращаю случайный серый гексагон

        return activeHexes[np.random.randint(len(activeHexes))]
    else:
        moveZoneNumber = (state[:, :, general_dict["gray"]] == 1) * (-1)  # определён только на серых
        expanded = False
        step = 0
        while True:
            expanded = False
            for hex in activeHexes:
                if moveZoneNumber[hex] != step:
                    continue
                for dir in range(6):
                    adj = getAdjacentHex(hex, dir)
                    if adj is None:
                        continue
                    if state[adj][general_dict["black"]] == 1:
                        continue
                    if moveZoneNumber[adj] != -1:
                        continue

                    moveZoneNumber[adj] = step + 1
                    expanded = True
            if not expanded:
                break
            step += 1

        result = None
        for hex in activeHexes:
            if result is None or moveZoneNumber[hex] > moveZoneNumber[result]:
                result = hex
        return result


def spawnProvince(spawnHex, startingPotential):
    global activeHexes
    global state
    global player1_provinces
    global player2_provinces
    isPlayer1 = state[spawnHex][P1_dict["player_hexes"]] == 1
    if isPlayer1:
        player1_provinces[1] = []
        player1_province_ambar_cost[1] = 12
    else:
        player2_provinces[1] = []
        player2_province_ambar_cost[1] = 12
    genPotential = np.zeros((height, width), "uint8")
    propagationList = []
    propagationList.append(spawnHex)
    genPotential[spawnHex] = startingPotential
    while len(propagationList) > 0:
        hex = propagationList.pop()
        if np.random.randint(startingPotential) > genPotential[hex]: continue
        state[hex][P1_dict["player_hexes"] if isPlayer1 else P2_dict["player_hexes"]] = 1
        if isPlayer1:
            player1_provinces[1].append(hex)
            state[hex][P1_dict["province_index"]] = 1  # теперь гексагон в первой провинции
        else:
            player2_provinces[1].append(hex)
            state[hex][P2_dict["province_index"]] = 1
        state[hex][general_dict["gray"]] = 0
        if genPotential[hex] == 0: continue
        for i in range(6):
            adjHex = getAdjacentHex(hex, i)
            if not adjHex is None and propagationList.count(adjHex) == 0 \
                    and state[adjHex][general_dict["black"]] == 0 and state[adjHex][general_dict["gray"]] == 1:
                genPotential[adjHex] = genPotential[hex] - 1
                propagationList.append(adjHex)
    # теперь дадим провинции деньги и доход записав эти значения в состояние, учитывая деревья
    if isPlayer1:
        number_of_trees = 0
        for hex in player1_provinces[1]:
            if state[hex][general_dict["palm"]] == 1 or state[hex][general_dict["pine"]] == 1:
                number_of_trees += 1
        income = len(player1_provinces[1]) - number_of_trees
        for hex in player1_provinces[1]:
            state[hex][P1_dict["income"]] = income
            state[hex][P1_dict["money"]] = 10  # Количество денег по умолчанию в начале игры
    else:
        number_of_trees = 0
        for hex in player2_provinces[1]:
            if state[hex][general_dict["palm"]] == 1 or state[hex][general_dict["pine"]] == 1:
                number_of_trees += 1
        income = len(player2_provinces[1]) - number_of_trees
        for hex in player2_provinces[1]:
            state[hex][P2_dict["income"]] = income
            state[hex][P2_dict["money"]] = 10


def spawnProvinces():
    global activeHexes
    global state
    quantity = 1  # по одной провинции на фракцию
    for i in range(quantity):
        for fraction in range(2):
            hex = findGoodPlaceForNewProvince(fraction)
            state[hex][P1_dict["player_hexes"] if fraction == 0 else P2_dict["player_hexes"]] = 1
            state[hex][general_dict["gray"]] = 0  # теперь гексагон не серый
            spawnProvince(hex, fraction + 1)  # игрок 2 имеет приемущество это нужно для баланса


def generate_random_game():
    global activeHexes
    global state
    # Далее createLand() - создание серых клеток
    N = 2  # число островов
    centers = []
    for i in range(N):
        hex = getRandomHexInsideBounds()
        centers.append(hex)
        spawnIsland(hex, 7)

    uniteIslandsWithRoads(centers)
    # Далее addTrees()

    addTrees()

    spawnProvinces()

    # Некотрые функции ниже я пропускаю так как считаю их лишними


def drawGame():
    global activeHexes
    global state
    x = np.arange(height)
    y = np.arange(width)
    xy = np.transpose([np.tile(x, len(y)), np.repeat(y, len(x))])
    color = []

    GRAY = (0.5, 0.5, 0.5)
    BLACK = (0, 0, 0)
    BLUE = (0, 0, 0.5)  # игрок 1
    RED = (0.5, 0, 0)  # игрок 2
    PINETREE = (0, 0.3, 0)
    PALMTREE = (0, 0.7, 0)
    for hex in xy:
        hex = int(hex[0]), int(hex[1])
        if state[hex][general_dict["black"]] == 1:
            color.append(BLACK)
            continue
        if state[hex][P1_dict["player_hexes"]] == 1:
            color.append(BLUE)
            continue
        if state[hex][P2_dict["player_hexes"]] == 1:
            color.append(RED)
            continue
        if state[hex][general_dict["pine"]] == 1:
            color.append(PINETREE)
            continue
        if state[hex][general_dict["palm"]] == 1:
            color.append(PALMTREE)
            continue
        if state[hex][general_dict["gray"]] == 1:
            color.append(GRAY)
            continue

    xy = np.apply_along_axis(computeCoordinates, 1, xy)

    # Make a list of colors cycling through the default series.

    fig, ax = plt.subplots()

    col = collections.RegularPolyCollection(6, rotation=0,
                                            sizes=(S,), offsets=xy,
                                            transOffset=ax.transData)
    trans = transforms.Affine2D().scale(fig.dpi / 72.0)
    col.set_transform(trans)  # the points to pixels transform
    ax.add_collection(col, autolim=True)
    col.set_color(color)
    ax.autoscale_view()
    ax.set_title('AntiyoyModel')
    plt.xlabel('Ось Х')
    plt.ylabel('Ось Y')
    plt.show()
