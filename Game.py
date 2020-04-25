import numpy as np

width = 14
height = 22
r = 1
state = np.zeros((height, width, 26), "uint8")
state[:, :, 0] = 1
player1 = 8
player2 = 19
black = 0
gray = 1
activeHexes = []


def getAdjecentHex(hex, direction):
    if direction == 0:
        if hex[1] == 0: return 0

        if hex[0] == 0 and hex[1] % 2 == 0: return 0

        if hex[1] % 2 == 1:
            return hex[0], hex[1] - 1
        else:
            return hex[0] - 1, hex[1] - 1

    if direction == 1:
        if hex[0] == 0: return 0
        return hex[0] - 1, hex[1]
    if direction == 2:
        if hex[1] == width - 1: return 0
        if hex[0] == 0 and hex[1] % 2 == 0: return 0
        if hex[1] % 2 == 1:
            return hex[0], hex[1] + 1
        else:
            return hex[0] - 1, hex[1] + 1
    if direction == 3:
        if hex[1] == width - 1: return 0
        if hex[0] == height - 1 and hex[1] % 2 == 1: return 0
        if hex[1] % 2 == 0:
            return hex[0], hex[1] + 1
        else:
            return hex[0] + 1, hex[1] + 1
    if direction == 4:
        if hex[0] == height - 1: return 0
        return hex[0] + 1, hex[1]
    if direction == 5:
        if hex[1] == 0 or (hex[0] == height - 1 and hex[1] % 2 == 1): return 0
        if hex[1] % 2 == 1:
            return hex[0] + 1, hex[1] - 1


def spawnIsland(startHex, size):
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
        x = state[hex, 1]
        state[hex, 1] = 1  # клетка из чёрной становится серой
        activeHexes.append(hex)
        state[hex, 0] = 0  # эта клетка больше не чёрная
        if genPotential[hex] == 0 or x == 1: continue
        for i in range(6):
            adjHex = getAdjecentHex(hex, i)
            if (adjHex != 0 and not gen[adjHex] and propagationList.count(adjHex) == 0):
                genPotential[adjHex] = genPotential[hex] - 1
                propagationList.append(adjHex)


def computeCoordinates(hex):
    return r * 3 ** 0.5 * hex[0] + r * ((1 - (-1) ** hex[1]) * 3 ** 0.5) / 4, r * (3 / 2) * hex[1]


def getHexByPos(x, y):
    j = int((2 / (r * 3)) * y)
    i = int((x - r * ((1 - (-1) ** j) * 3 ** 0.5) / 4) / (r * 3 ** 0.5))
    if i < 0 or i > height - 1 or j < 0 or j > width - 1: return 0
    return i, j


def uniteIslandsWithRoads(centers):
    startPoint = computeCoordinates(centers[0])
    endPoint = computeCoordinates(centers[1])
    distance = ((startPoint[0] - endPoint[0]) ** 2 + (startPoint[1] - startPoint[1]) ** 2) ** 0.5
    angle = np.angle([complex(startPoint[0], startPoint[1]), complex(endPoint[0], endPoint[1])])
    delta = r / 2
    n = (int)(distance / delta)
    for i in range(n):
        currentX = startPoint[0] + delta * i * np.cos(angle)
        currentY = startPoint[1] + delta * i * np.sin(angle)
        hex = getHexByPos(currentX, currentY)
        spawnIsland(hex, 2)


def getRandomHexInsideBounds():
    return np.random.randint(height), np.random.randint(width)


def isNearWater(hex):
    for i in range(6):
        adj = getAdjecentHex(hex, i)
        if adj == 0:
            continue
        if state[getAdjecentHex(hex, i), 0] == 1:
            return True
    return False


def spawnTree(hex):
    if isNearWater(hex):
        state[hex, 2] = 1  # Добавил пальму
    else:
        state[hex, 3] = 1  # Добавил ёлку


def addTrees():
    for hex in state[:, :, 1]:
        if state[hex, 0] == 1:
            continue
        if np.random.rand() < 0.1: spawnTree(hex)


def findGoodPlaceForNewProvince(fraction):
    if (fraction == 0):  # Возвращаю случайный серый гексагон

        grayHex = np.where(state[:, :, gray] == 1)
        return grayHex[np.random.randint(len(grayHex))]
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
                    if adj == 0: continue
                    if state[adj, black] == 1: continue
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
    genPotential = np.zeros((height, width), "uint8")
    propagationList = []
    propagationList.append(spawHex)
    while len(propagationList) > 0:
        hex = propagationList.pop()
        if np.random.randint(startingPotential) > genPotential[hex]: continue
        state[hex, player1 if state[spawHex, player1] == 1 else player2] = 1
        state[hex, gray] = 0
        if genPotential[hex] == 0: continue
        for i in range(6):
            adjHex = getAdjecentHex(i)
            if adjHex != 0 and not propagationList.count(adjHex) == 0 \
                    and state[adjHex, black] == 0 and state[adjHex, gray] == 1:
                genPotential[adjHex] = genPotential[hex] - 1
                propagationList.append(adjHex)


def spawnProvinces():
    quantity = 1  # по одной провинции на фракцию
    for i in range(quantity):
        for fraction in range(2):
            hex = findGoodPlaceForNewProvince(fraction)
            state[hex, player1] = 1
            state[hex, 1] = fraction  # теперь гексагон не серый, а принадлежит игроку 1
            spawnProvince(hex, 2)


def generate_random_game():
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


generate_random_game()

print(state[0, 0, 0])
