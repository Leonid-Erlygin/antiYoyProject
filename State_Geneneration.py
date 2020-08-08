import numpy as np

import matplotlib.pyplot as plt

r = 20  # пикселей
width = 14  # параметры поля, измеряемые в гексагонах
height = 22

state = np.zeros((height, width, 29), "uint8")
unit_type = np.zeros((height, width),
                     "uint8")  # вспомогательный массив, указывающий тип юнита находящегося в данной клетке
# юнит либо у игрока 1, либо у игрока 2
P1_dict = {"unit1": 4, "unit2": 5, "unit3": 6, "unit4": 7, "player_hexes": 8, "tower1": 9, "tower2": 10, "ambar": 11,
           "town": 12, "income": 13, "money": 14, "province_index": 15}
general_dict = {"black": 0, "gray": 1, "palm": 2, "pine": 3, "graves": 28}
P2_dict = {"unit1": 16, "unit2": 17, "unit3": 18, "unit4": 19, "player_hexes": 20, "tower1": 21, "tower2": 22,
           "ambar": 23, "town": 24, "income": 25, "money": 26, "province_index": 27}
player1_provinces = {}
player2_provinces = {}

state[:, :, general_dict["black"]] = 1

player1_province_ambar_cost = {}
player2_province_ambar_cost = {}

activeHexes = []


def getAdjacentHex(hexagon, direction):
    if direction == 0:
        if hexagon[1] == 0:
            return None

        if hexagon[0] == 0 and hexagon[1] % 2 == 0:
            return None

        if hexagon[1] % 2 == 1:
            return hexagon[0], hexagon[1] - 1
        else:
            return hexagon[0] - 1, hexagon[1] - 1

    if direction == 1:
        if hexagon[0] == 0:
            return None
        return hexagon[0] - 1, hexagon[1]
    if direction == 2:
        if hexagon[1] == width - 1:
            return None
        if hexagon[0] == 0 and hexagon[1] % 2 == 0:
            return None
        if hexagon[1] % 2 == 1:
            return hexagon[0], hexagon[1] + 1
        else:
            return hexagon[0] - 1, hexagon[1] + 1
    if direction == 3:
        if hexagon[1] == width - 1:
            return None
        if hexagon[0] == height - 1 and hexagon[1] % 2 == 1:
            return None
        if hexagon[1] % 2 == 0:
            return hexagon[0], hexagon[1] + 1
        else:
            return hexagon[0] + 1, hexagon[1] + 1
    if direction == 4:
        if hexagon[0] == height - 1:
            return None
        return hexagon[0] + 1, hexagon[1]
    if direction == 5:
        if hexagon[1] == 0 or (hexagon[0] == height - 1 and hexagon[1] % 2 == 1):
            return None
        if hexagon[1] % 2 == 1:
            return hexagon[0] + 1, hexagon[1] - 1


def get_adjacent_hexes(hexagon):
    """
    Возвращает список прилегающих гексагонов
    :param hexagon: Гексагон, для которого ищем соседей
    :return:
    """
    adjacent = []
    for i in range(6):
        adj = getAdjacentHex(hexagon, i)
        if adj is not None:
            adjacent.append(adj)
    return adjacent


def get_adjacent_friendly_hexes(hexagon, player):
    """
    Возвращает список дружественных прилегающих гексагонов
    :param hexagon: Гексагон, для которого ищем соседей
    :param player: Игрок
    :return:
    """
    adjacent = []
    layer = P1_dict["player_hexes"] if player == 1 else P2_dict["player_hexes"]
    for i in range(6):
        adj = getAdjacentHex(hexagon, i)
        if adj is not None and state[adj][layer] == 1:
            adjacent.append(adj)
    return adjacent


def spawnIsland(start_hex, size):
    global activeHexes
    global state
    gen = np.zeros((height, width), "bool")  # матрица которая будет указывать сгенерировали ли
    # что-то клетка или нет
    gen_potential = np.zeros((height, width), "uint8")  # Число - потенциал генирации
    gen_potential[start_hex] = size
    propagation_list = [start_hex]
    while len(propagation_list) > 0:
        hexagon = propagation_list.pop()
        gen[start_hex] = 1

        if np.random.randint(low=0, high=size) > gen_potential[hexagon]:
            continue
        x = state[hexagon][general_dict["gray"]] != 1
        if x:
            activeHexes.append(hexagon)
        state[hexagon][general_dict["gray"]] = 1  # клетка из чёрной становится серой
        state[hexagon][general_dict["black"]] = 0  # эта клетка больше не чёрная

        if gen_potential[hexagon] == 0 or not x:
            continue

        for i in range(6):
            adj_hex = getAdjacentHex(hexagon, i)
            if adj_hex is not None and not gen[adj_hex] and propagation_list.count(adj_hex) == 0:
                gen_potential[adj_hex] = gen_potential[hexagon] - 1
                propagation_list.append(adj_hex)


def computeCoordinates(hexagon):
    x = r * 3 ** 0.5 * hexagon[0] + r * ((1 - (-1) ** hexagon[1]) * 3 ** 0.5) / 4
    y = r * (3 / 2) * hexagon[1]
    return x, y


def getHexByPos(x, y):
    j = int((2 / (r * 3)) * y)
    i = int((x - r * ((1 - (-1) ** j) * 3 ** 0.5) / 4) / (r * 3 ** 0.5))
    if i < 0 or i > height - 1 or j < 0 or j > width - 1:
        return 0
    return i, j


def uniteIslandsWithRoads(centers):
    global activeHexes
    global state
    start_point = computeCoordinates(centers[0])
    end_point = computeCoordinates(centers[1])
    distance = ((start_point[0] - end_point[0]) ** 2 + (start_point[1] - end_point[1]) ** 2) ** 0.5
    angle = np.angle([complex(end_point[0] - start_point[0], end_point[1] - start_point[1])])
    delta = r / 2
    n = int(distance / delta)
    prev = (-1, -1)
    for i in range(n):
        currentX = start_point[0] + delta * i * np.cos(angle)
        currentY = start_point[1] + delta * i * np.sin(angle)
        hexagon = getHexByPos(currentX, currentY)
        # spawnIsland(hex, 2)
        if hexagon != prev:
            spawnIsland(hexagon, 2)
            prev = hexagon


def getRandomHexInsideBounds():
    return np.random.randint(height), np.random.randint(width)


def isNearWater(hexagon):
    for i in range(6):
        adj = getAdjacentHex(hexagon, i)
        if adj is None:
            continue
        if state[adj][general_dict["black"]] == 1:
            return True
    return False


def spawnTree(hexagon):
    global activeHexes
    global state
    if isNearWater(hexagon):
        state[hexagon][general_dict["palm"]] = 1  # Добавил пальму
    else:
        state[hexagon][general_dict["pine"]] = 1  # Добавил ёлку


def addTrees():
    for hexagon in activeHexes:
        if np.random.rand() < 0.1:
            spawnTree(hexagon)


def findGoodPlaceForNewProvince(fraction):
    global activeHexes
    global state
    if fraction == 0:  # Возвращаю случайный серый гексагон

        return activeHexes[np.random.randint(len(activeHexes))]
    else:
        moveZoneNumber = (state[:, :, general_dict["gray"]] == 1) * (-1)  # определён только на серых

        step = 0
        while True:
            expanded = False
            for hexagon in activeHexes:
                if moveZoneNumber[hexagon] != step:
                    continue
                for direction in range(6):
                    adj = getAdjacentHex(hexagon, direction)
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
        for hexagon in activeHexes:
            if result is None or moveZoneNumber[hexagon] > moveZoneNumber[result]:
                result = hexagon
        return result


def spawnProvince(spawn_hex, starting_potential):
    global activeHexes
    global state
    global player1_provinces
    global player2_provinces
    isPlayer1 = state[spawn_hex][P1_dict["player_hexes"]] == 1
    if isPlayer1:
        player1_provinces[1] = []
        player1_province_ambar_cost[1] = 12
    else:
        player2_provinces[1] = []
        player2_province_ambar_cost[1] = 12
    genPotential = np.zeros((height, width), "uint8")
    propagationList = [spawn_hex]
    genPotential[spawn_hex] = starting_potential
    while len(propagationList) > 0:
        hexagon = propagationList.pop()
        if np.random.randint(starting_potential) > genPotential[hexagon]:
            continue
        state[hexagon][P1_dict["player_hexes"] if isPlayer1 else P2_dict["player_hexes"]] = 1
        if isPlayer1:
            player1_provinces[1].append(hexagon)
            state[hexagon][P1_dict["province_index"]] = 1  # теперь гексагон в первой провинции
        else:
            player2_provinces[1].append(hexagon)
            state[hexagon][P2_dict["province_index"]] = 1
        state[hexagon][general_dict["gray"]] = 0
        if genPotential[hexagon] == 0:
            continue
        for i in range(6):
            adjHex = getAdjacentHex(hexagon, i)
            if adjHex is not None and propagationList.count(adjHex) == 0 \
                    and state[adjHex][general_dict["black"]] == 0 and state[adjHex][general_dict["gray"]] == 1:
                genPotential[adjHex] = genPotential[hexagon] - 1
                propagationList.append(adjHex)
    # теперь дадим провинции деньги и доход записав эти значения в состояние, учитывая деревья
    if isPlayer1:
        number_of_trees = 0
        for hexagon in player1_provinces[1]:
            if state[hexagon][general_dict["palm"]] == 1 or state[hexagon][general_dict["pine"]] == 1:
                number_of_trees += 1
        income = len(player1_provinces[1]) - number_of_trees
        for hexagon in player1_provinces[1]:
            state[hexagon][P1_dict["income"]] = income
            state[hexagon][P1_dict["money"]] = 10  # Количество денег по умолчанию в начале игры
    else:
        number_of_trees = 0
        for hexagon in player2_provinces[1]:
            if state[hexagon][general_dict["palm"]] == 1 or state[hexagon][general_dict["pine"]] == 1:
                number_of_trees += 1
        income = len(player2_provinces[1]) - number_of_trees
        for hexagon in player2_provinces[1]:
            state[hexagon][P2_dict["income"]] = income
            state[hexagon][P2_dict["money"]] = 10


def spawnProvinces():
    global activeHexes
    global state
    quantity = 1  # по одной провинции на фракцию
    for i in range(quantity):
        for fraction in range(2):
            hexagon = findGoodPlaceForNewProvince(fraction)
            state[hexagon][P1_dict["player_hexes"] if fraction == 0 else P2_dict["player_hexes"]] = 1
            state[hexagon][general_dict["gray"]] = 0  # теперь гексагон не серый
            spawnProvince(hexagon, fraction + 1)  # игрок 2 имеет приемущество это нужно для баланса


def generate_random_game():
    global activeHexes
    global state
    # Далее createLand() - создание серых клеток
    N = 2  # число островов
    centers = []
    for i in range(N):
        hexagon = getRandomHexInsideBounds()
        centers.append(hexagon)
        spawnIsland(hexagon, 7)

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

    picture_width = 800
    picture_height = 430
    dpi = 300
    hex_size = 0.089

    pictures = {"town": plt.imread('assets/field_elements/castle.png'),
                "unit1": plt.imread('assets/field_elements/man0.png'),
                "unit2": plt.imread('assets/field_elements/man1.png'),
                "unit3": plt.imread('assets/field_elements/man2.png'),
                "unit4": plt.imread('assets/field_elements/man3.png'),
                "tower1": plt.imread('assets/field_elements/tower.png'),
                "tower2": plt.imread('assets/field_elements/strong_tower.png'),
                "tree": plt.imread('assets/field_elements/palm.png'),
                "ambar": plt.imread('assets/field_elements/farm1.png'),
                "grave": plt.imread('assets/field_elements/grave.png')
                }
    hexagons = {"black": plt.imread('assets/hex_black.png'),
                "gray": plt.imread('assets/hex_gray.png'),
                "blue": plt.imread('assets/hex_blue.png'),
                "red": plt.imread('assets/hex_red.png'),
                }
    entity_distribution = {"unit1": [], "unit2": [], "unit3": [], "unit4": [], "tower1": [], "tower2": [], "tree": [],
                           "ambar": [], "town": [], "grave": []}
    fig = plt.figure(figsize=(picture_width / dpi, picture_height / dpi), dpi=dpi)

    for hexagon in xy:
        hexagon = int(hexagon[0]), int(hexagon[1])
        x, y = computeCoordinates(hexagon)
        if state[hexagon][general_dict["black"]] == 1:
            new_ax = fig.add_axes(
                [x / picture_width, y / picture_height, hex_size, hex_size],
                zorder=1)
            new_ax.axis('off')
            new_ax.imshow(hexagons["black"])

        elif state[hexagon][P1_dict["player_hexes"]] == 1:
            new_ax = fig.add_axes(
                [x / picture_width, y / picture_height, hex_size, hex_size],
                zorder=1)
            new_ax.axis('off')
            new_ax.imshow(hexagons["blue"])
        elif state[hexagon][P2_dict["player_hexes"]] == 1:
            new_ax = fig.add_axes(
                [x / picture_width, y / picture_height, hex_size, hex_size],
                zorder=1)
            new_ax.axis('off')
            new_ax.imshow(hexagons["red"])
        elif state[hexagon][general_dict["gray"]] == 1:
            new_ax = fig.add_axes(
                [x / picture_width, y / picture_height, hex_size, hex_size],
                zorder=1)
            new_ax.axis('off')
            new_ax.imshow(hexagons["gray"])
        if state[hexagon][general_dict["pine"]] == 1 or state[hexagon][general_dict["pine"]] == 1:
            entity_distribution["tree"].append(hexagon)
        if unit_type[hexagon] != 0:
            unit = "unit" + str(unit_type)
            entity_distribution[unit].append(hexagon)
        if state[hexagon][P1_dict["tower1"]] == 1:
            entity_distribution["tower1"].append(hexagon)
        if state[hexagon][P1_dict["tower2"]] == 1:
            entity_distribution["tower2"].append(hexagon)
        if state[hexagon][P1_dict["town"]] == 1:
            entity_distribution["town"].append(hexagon)

    entity_distribution["tower2"].append((4, 0))
    for entity, hex_list in entity_distribution.items():
        for hexagon in hex_list:
            x, y = computeCoordinates(hexagon)
            x -= r / 10
            y += r / 10
            new_ax = fig.add_axes(
                [x / picture_width, y / picture_height, hex_size, hex_size],
                zorder=2)
            new_ax.axis('off')
            new_ax.imshow(pictures[entity])

    plt.xlabel('Ось Х')
    plt.ylabel('Ось Y')

    plt.show()
