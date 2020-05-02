import numpy as np

import matplotlib.pyplot as plt
from matplotlib import collections, colors, transforms

width = 14
height = 22
S = 200  # площадь описываещего круга
r = (S / np.pi) ** 0.5
state = np.zeros((height, width, 26), "uint8")
state[:, :, 0] = 1
player1 = 8
player2 = 19
black = 0
gray = 1
palm = 2
pine = 3
activeHexes = []


def getAdjecentHex(hex, direction):
    if direction == 0:
        if hex[1] == 0: return None

        if hex[0] == 0 and hex[1] % 2 == 0: return None

        if hex[1] % 2 == 1:
            return hex[0], hex[1] - 1
        else:
            return hex[0] - 1, hex[1] - 1

    if direction == 1:
        if hex[0] == 0: return None
        return hex[0] - 1, hex[1]
    if direction == 2:
        if hex[1] == width - 1: return None
        if hex[0] == 0 and hex[1] % 2 == 0: return None
        if hex[1] % 2 == 1:
            return hex[0], hex[1] + 1
        else:
            return hex[0] - 1, hex[1] + 1
    if direction == 3:
        if hex[1] == width - 1: return None
        if hex[0] == height - 1 and hex[1] % 2 == 1: return None
        if hex[1] % 2 == 0:
            return hex[0], hex[1] + 1
        else:
            return hex[0] + 1, hex[1] + 1
    if direction == 4:
        if hex[0] == height - 1: return None
        return hex[0] + 1, hex[1]
    if direction == 5:
        if hex[1] == 0 or (hex[0] == height - 1 and hex[1] % 2 == 1): return None
        if hex[1] % 2 == 1:
            return hex[0] + 1, hex[1] - 1


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
        x = state[hex][gray] != 1
        if x: activeHexes.append(hex)
        state[hex][gray] = 1  # клетка из чёрной становится серой
        state[hex][black] = 0  # эта клетка больше не чёрная

        if genPotential[hex] == 0 or not x: continue

        for i in range(6):
            adjHex = getAdjecentHex(hex, i)
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
        #spawnIsland(hex, 2)
        if hex != prev:
            spawnIsland(hex, 2)
            prev = hex

def getRandomHexInsideBounds():
    return np.random.randint(height), np.random.randint(width)


def isNearWater(hex):
    for i in range(6):
        adj = getAdjecentHex(hex, i)
        if adj is None:
            continue
        if state[adj][black] == 1:
            return True
    return False


def spawnTree(hex):
    global activeHexes
    global state
    if isNearWater(hex):
        state[hex][palm] = 1  # Добавил пальму
    else:
        state[hex][pine] = 1  # Добавил ёлку


def addTrees():
    for hex in activeHexes:
        if np.random.rand() < 0.1: spawnTree(hex)


def findGoodPlaceForNewProvince(fraction):
    global activeHexes
    global state
    if (fraction == 0):  # Возвращаю случайный серый гексагон

        return activeHexes[np.random.randint(len(activeHexes))]
    else:
        moveZoneNumber = (state[:, :, gray] == 1) * (-1)  # определён только на серых
        expanded = False
        step = 0
        while True:
            expanded = False
            for hex in activeHexes:
                if moveZoneNumber[hex] != step: continue
                for dir in range(6):
                    adj = getAdjecentHex(hex, dir)
                    if adj is None: continue
                    if state[adj][black] == 1: continue
                    if moveZoneNumber[adj] != -1: continue

                    moveZoneNumber[adj] = step + 1
                    expanded = True
            if not expanded: break
            step += 1

        result = None
        for hex in activeHexes:
            if result is None or moveZoneNumber[hex] > moveZoneNumber[result]:
                result = hex
        return result


def spawnProvince(spawHex, startingPotential):
    global activeHexes
    global state
    genPotential = np.zeros((height, width), "uint8")
    propagationList = []
    propagationList.append(spawHex)
    genPotential[spawHex] = startingPotential
    while len(propagationList) > 0:
        hex = propagationList.pop()
        if np.random.randint(startingPotential) > genPotential[hex]: continue
        state[hex][player1 if state[spawHex][player1] == 1 else player2] = 1
        state[hex][gray] = 0
        if genPotential[hex] == 0: continue
        for i in range(6):
            adjHex = getAdjecentHex(hex,i)
            if not adjHex is None and propagationList.count(adjHex) == 0 \
                    and state[adjHex][black] == 0 and state[adjHex][gray] == 1:
                genPotential[adjHex] = genPotential[hex] - 1
                propagationList.append(adjHex)


def spawnProvinces():
    global activeHexes
    global state
    quantity = 1  # по одной провинции на фракцию
    for i in range(quantity):
        for fraction in range(2):
            hex = findGoodPlaceForNewProvince(fraction)
            state[hex][player1 if fraction == 0 else player2] = 1
            state[hex][gray] = 0  # теперь гексагон не серый
            spawnProvince(hex, fraction+1)#игрок 2 имеет приемущество это нужно для баланса





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
    PINETREE = (0,0.3,0)
    PALMTREE = (0,0.7,0)
    for hex in xy:
        hex = int(hex[0]), int(hex[1])
        if state[hex][black] == 1:
            color.append(BLACK)
            continue
        if state[hex][player1] == 1:
            color.append(BLUE)
            continue
        if state[hex][player2] == 1:
            color.append(RED)
            continue
        if state[hex][pine] == 1:
            color.append(PINETREE)
            continue
        if state[hex][palm] == 1:
            color.append(PALMTREE)
            continue
        if state[hex][gray] == 1:
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
