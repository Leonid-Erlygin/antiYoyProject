import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import collections
from numpy.random import RandomState
from pathlib import Path


class GameState:
    def __init__(self, seed, r, width, height, assets_path):
        """
        params:
        r - пикселей
        width, height - параметры поля, измеряемые в гексагонах
        """
        self.assets_path = Path(assets_path)
        self.r = r
        self.width = width
        self.height = height
        self.rs = RandomState(seed)
        self.state_matrix = np.zeros((self.height, self.width, 29), "int32")

        self.unit_type = np.zeros(
            (self.height, self.width), "uint8"
        )  # вспомогательный массив, указывающий тип юнита находящегося в данной клетке
        # юнит либо у игрока 1, либо у игрока 2
        self.P1_dict = {
            "unit1": 4,
            "unit2": 5,
            "unit3": 6,
            "unit4": 7,
            "player_hexes": 8,
            "tower1": 9,
            "tower2": 10,
            "ambar": 11,
            "town": 12,
            "income": 13,
            "money": 14,
            "province_index": 15,
        }

        self.P2_dict = {
            "unit1": 16,
            "unit2": 17,
            "unit3": 18,
            "unit4": 19,
            "player_hexes": 20,
            "tower1": 21,
            "tower2": 22,
            "ambar": 23,
            "town": 24,
            "income": 25,
            "money": 26,
            "province_index": 27,
        }
        self.general_dict = {"black": 0, "gray": 1, "palm": 2, "pine": 3, "graves": 28}
        self.state_matrix[:, :, self.general_dict["black"]] = 1

        self.player1_provinces = {}
        self.player2_provinces = {}
        self.player1_province_ambar_cost = {}
        self.player2_province_ambar_cost = {}
        self.activeHexes = []
        self.tree_list = []
        self.units_list = []
        self.p1_units_list = []
        self.p2_units_list = []
        self.graves_list = []
        self.p1_last_expanded_step = 0
        self.p2_last_expanded_step = 0
        self.dead_hexes = (
            []
        )  # сюда записываются вражеские гексагоны(единичные провинции), которые в начале хода
        # противника будут убиты

    def getAdjacentHex(self, hexagon, direction):
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
            if hexagon[1] == self.width - 1:
                return None
            if hexagon[0] == 0 and hexagon[1] % 2 == 0:
                return None
            if hexagon[1] % 2 == 1:
                return hexagon[0], hexagon[1] + 1
            else:
                return hexagon[0] - 1, hexagon[1] + 1
        if direction == 3:
            if hexagon[1] == self.width - 1:
                return None
            if hexagon[0] == self.height - 1 and hexagon[1] % 2 == 1:
                return None
            if hexagon[1] % 2 == 0:
                return hexagon[0], hexagon[1] + 1
            else:
                return hexagon[0] + 1, hexagon[1] + 1
        if direction == 4:
            if hexagon[0] == self.height - 1:
                return None
            return hexagon[0] + 1, hexagon[1]
        if direction == 5:
            if hexagon[1] == 0 or (
                hexagon[0] == self.height - 1 and hexagon[1] % 2 == 1
            ):
                return None
            if hexagon[1] % 2 == 1:
                return hexagon[0] + 1, hexagon[1] - 1
            else:
                return hexagon[0], hexagon[1] - 1

    def get_adjacent_hexes(self, hexagon):
        """
        Возвращает список прилегающих гексагонов
        :param hexagon: Гексагон, для которого ищем соседей
        :return:
        """
        adjacent = []
        for i in range(6):
            adj = self.getAdjacentHex(hexagon, i)
            if adj is not None:
                adjacent.append(adj)
        return adjacent

    def get_adjacent_friendly_hexes(self, hexagon, player):
        """
        :param hexagon: Гексагон, для которого ищем соседей
        :param player: Игрок
        :return:
        """
        adjacent = []
        layer = (
            self.P1_dict["player_hexes"]
            if player == 0
            else self.P2_dict["player_hexes"]
        )
        for i in range(6):
            adj = self.getAdjacentHex(hexagon, i)
            if adj is not None and self.state_matrix[adj][layer] == 1:
                adjacent.append(adj)
        return adjacent

    def spawnIsland(self, start_hex, size):
        gen = np.zeros(
            (self.height, self.width), "bool"
        )  # матрица которая будет указывать сгенерировали ли
        # что-то клетка или нет
        gen_potential = np.zeros(
            (self.height, self.width), "uint8"
        )  # Число - потенциал генирации
        gen_potential[start_hex] = size
        propagation_list = [start_hex]
        while len(propagation_list) > 0:
            hexagon = propagation_list.pop()
            gen[start_hex] = 1

            if self.rs.randint(low=0, high=size) > gen_potential[hexagon]:
                continue
            x = self.state_matrix[hexagon][self.general_dict["gray"]] != 1
            if x:
                self.activeHexes.append(hexagon)
            self.state_matrix[hexagon][
                self.general_dict["gray"]
            ] = 1  # клетка из чёрной становится серой
            self.state_matrix[hexagon][
                self.general_dict["black"]
            ] = 0  # эта клетка больше не чёрная

            if gen_potential[hexagon] == 0 or not x:
                continue

            for i in range(6):
                adj_hex = self.getAdjacentHex(hexagon, i)
                if (
                    adj_hex is not None
                    and not gen[adj_hex]
                    and propagation_list.count(adj_hex) == 0
                ):
                    gen_potential[adj_hex] = gen_potential[hexagon] - 1
                    propagation_list.append(adj_hex)

    def computeCoordinates(self, hexagon):
        x = (
            self.r * 3**0.5 * hexagon[0]
            + self.r * ((1 - (-1) ** hexagon[1]) * 3**0.5) / 4
        )
        y = self.r * (3 / 2) * hexagon[1]
        return x, y

    def getHexByPos(self, x, y):
        j = int((2 / (self.r * 3)) * y)
        i = int((x - self.r * ((1 - (-1) ** j) * 3**0.5) / 4) / (self.r * 3**0.5))
        if i < 0 or i > self.height - 1 or j < 0 or j > self.width - 1:
            return 0
        return i, j

    def uniteIslandsWithRoads(self, centers):
        start_point = self.computeCoordinates(centers[0])
        end_point = self.computeCoordinates(centers[1])
        distance = (
            (start_point[0] - end_point[0]) ** 2 + (start_point[1] - end_point[1]) ** 2
        ) ** 0.5
        angle = np.angle(
            [complex(end_point[0] - start_point[0], end_point[1] - start_point[1])]
        )
        delta = self.r / 2
        n = int(distance / delta)
        prev = (-1, -1)
        for i in range(n):
            currentX = start_point[0] + delta * i * np.cos(angle)
            currentY = start_point[1] + delta * i * np.sin(angle)
            hexagon = self.getHexByPos(currentX, currentY)
            # spawnIsland(hex, 2)
            if hexagon != prev:
                self.spawnIsland(hexagon, 2)
                prev = hexagon

    def getRandomHexInsideBounds(self):
        return self.rs.randint(self.height), self.rs.randint(self.width)

    def isNearWater(self, hexagon):
        for i in range(6):
            adj = self.getAdjacentHex(hexagon, i)
            if adj is None:
                continue
            if self.state_matrix[adj][self.general_dict["black"]] == 1:
                return True
        return False

    def spawnTree(self, hexagon):
        self.tree_list.append(hexagon)
        if self.isNearWater(hexagon):
            self.state_matrix[hexagon][self.general_dict["palm"]] = 1  # Добавил пальму
        else:
            self.state_matrix[hexagon][self.general_dict["pine"]] = 1  # Добавил ёлку

    def addTrees(self):
        for hexagon in self.activeHexes:
            if (
                self.rs.rand() < 0.1
                and self.state_matrix[hexagon][self.P1_dict["town"]] == 0
                and self.state_matrix[hexagon][self.P2_dict["town"]] == 0
            ):
                self.spawnTree(hexagon)

    def findGoodPlaceForNewProvince(self, fraction):
        if fraction == 0:  # Возвращаю случайный серый гексагон
            return self.activeHexes[self.rs.randint(len(self.activeHexes))]
        else:
            moveZoneNumber = (
                self.state_matrix[:, :, self.general_dict["gray"]] == 1
            ) * (
                -1
            )  # определён только на серых

            step = 0
            while True:
                expanded = False
                for hexagon in self.activeHexes:
                    if moveZoneNumber[hexagon] != step:
                        continue
                    for direction in range(6):
                        adj = self.getAdjacentHex(hexagon, direction)
                        if adj is None:
                            continue
                        if self.state_matrix[adj][self.general_dict["black"]] == 1:
                            continue
                        if moveZoneNumber[adj] != -1:
                            continue

                        moveZoneNumber[adj] = step + 1
                        expanded = True
                if not expanded:
                    break
                step += 1

            result = None
            for hexagon in self.activeHexes:
                if result is None or moveZoneNumber[hexagon] > moveZoneNumber[result]:
                    result = hexagon
            return result

    def spawnProvince(self, spawn_hex, starting_potential):
        isPlayer1 = self.state_matrix[spawn_hex][self.P1_dict["player_hexes"]] == 1
        if isPlayer1:
            self.player1_provinces[1] = []
            self.player1_province_ambar_cost[1] = 12
        else:
            self.player2_provinces[1] = []
            self.player2_province_ambar_cost[1] = 12
        genPotential = np.zeros((self.height, self.width), "uint8")
        propagationList = [spawn_hex]
        genPotential[spawn_hex] = starting_potential
        while len(propagationList) > 0:
            hexagon = propagationList.pop()
            if self.rs.randint(starting_potential) > genPotential[hexagon]:
                continue
            self.state_matrix[hexagon][
                self.P1_dict["player_hexes"]
                if isPlayer1
                else self.P2_dict["player_hexes"]
            ] = 1
            if isPlayer1:
                self.player1_provinces[1].append(hexagon)
                self.state_matrix[hexagon][
                    self.P1_dict["province_index"]
                ] = 1  # теперь гексагон в первой провинции
            else:
                self.player2_provinces[1].append(hexagon)
                self.state_matrix[hexagon][self.P2_dict["province_index"]] = 1
            self.state_matrix[hexagon][self.general_dict["gray"]] = 0
            if genPotential[hexagon] == 0:
                continue
            for i in range(6):
                adjHex = self.getAdjacentHex(hexagon, i)
                if (
                    adjHex is not None
                    and propagationList.count(adjHex) == 0
                    and self.state_matrix[adjHex][self.general_dict["black"]] == 0
                    and self.state_matrix[adjHex][self.general_dict["gray"]] == 1
                ):
                    genPotential[adjHex] = genPotential[hexagon] - 1
                    propagationList.append(adjHex)
        # теперь дадим провинции деньги и доход записав эти значения в состояние, учитывая деревья
        number_of_trees = 0
        if isPlayer1:
            for hexagon in self.player1_provinces[1]:
                if (
                    self.state_matrix[hexagon][self.general_dict["palm"]] == 1
                    or self.state_matrix[hexagon][self.general_dict["pine"]] == 1
                ):
                    number_of_trees += 1
            income = len(self.player1_provinces[1]) - number_of_trees
            for hexagon in self.player1_provinces[1]:
                self.state_matrix[hexagon][self.P1_dict["income"]] = income
                self.state_matrix[hexagon][
                    self.P1_dict["money"]
                ] = 10  # Количество денег по умолчанию в начале игры
        else:
            for hexagon in self.player2_provinces[1]:
                if (
                    self.state_matrix[hexagon][self.general_dict["palm"]] == 1
                    or self.state_matrix[hexagon][self.general_dict["pine"]] == 1
                ):
                    number_of_trees += 1
            income = len(self.player2_provinces[1]) - number_of_trees
            for hexagon in self.player2_provinces[1]:
                self.state_matrix[hexagon][self.P2_dict["income"]] = income
                self.state_matrix[hexagon][self.P2_dict["money"]] = 10

    def spawnProvinces(self):
        quantity = 1  # по одной провинции на фракцию
        for i in range(quantity):
            for fraction in range(2):
                hexagon = self.findGoodPlaceForNewProvince(fraction)
                self.state_matrix[hexagon][self.general_dict["palm"]] = 0
                self.state_matrix[hexagon][self.general_dict["pine"]] = 0

                self.state_matrix[hexagon][
                    self.P1_dict["player_hexes"]
                    if fraction == 0
                    else self.P2_dict["player_hexes"]
                ] = 1
                self.state_matrix[hexagon][
                    self.P1_dict["town"] if fraction == 0 else self.P2_dict["town"]
                ] = 1  # в этом гексагоне есть город
                self.state_matrix[hexagon][
                    self.general_dict["gray"]
                ] = 0  # теперь гексагон не серый
                self.spawnProvince(
                    hexagon, fraction + 1
                )  # игрок 2 имеет приемущество это нужно для баланса

    def generate_random_game(self):
        # Далее createLand() - создание серых клеток
        N = 2  # число островов
        centers = []
        for _ in range(N):
            hexagon = self.getRandomHexInsideBounds()
            centers.append(hexagon)
            self.spawnIsland(hexagon, 7)

        self.uniteIslandsWithRoads(centers)
        # Далее addTrees()

        self.addTrees()
        self.spawnProvinces()

        # Некотрые функции ниже я пропускаю так как считаю их лишними

    def draw_game(self, plot_save_path: Path):
        x = np.arange(self.height)
        y = np.arange(self.width)
        xy = np.transpose([np.tile(x, len(y)), np.repeat(y, len(x))])

        picture_width = 800
        picture_height = 430
        dpi = 300
        hex_size = 0.089

        pictures = {
            "town": plt.imread(self.assets_path / "field_elements/castle.png"),
            "unit1": plt.imread(self.assets_path / "field_elements/man0.png"),
            "unit2": plt.imread(self.assets_path / "field_elements/man1.png"),
            "unit3": plt.imread(self.assets_path / "field_elements/man2.png"),
            "unit4": plt.imread(self.assets_path / "field_elements/man3.png"),
            "tower1": plt.imread(self.assets_path / "field_elements/tower.png"),
            "tower2": plt.imread(self.assets_path / "field_elements/strong_tower.png"),
            "palm": plt.imread(self.assets_path / "field_elements/palm.png"),
            "pine": plt.imread(self.assets_path / "field_elements/pine.png"),
            "ambar": plt.imread(self.assets_path / "field_elements/farm1.png"),
            "grave": plt.imread(self.assets_path / "field_elements/grave.png"),
        }
        entity_distribution = {
            "unit1": [],
            "unit2": [],
            "unit3": [],
            "unit4": [],
            "tower1": [],
            "tower2": [],
            "palm": [],
            "pine": [],
            "ambar": [],
            "town": [],
            "grave": [],
        }
        fig = plt.figure(figsize=(picture_width / dpi, picture_height / dpi), dpi=dpi)

        ax = fig.add_axes([0, 0, picture_width / dpi, picture_height / dpi], zorder=1)
        ax.axis("off")
        color = []
        GRAY = (0.5, 0.5, 0.5)
        BLACK = (0, 0, 0)
        BLUE = (0, 0, 0.5)  # игрок 1
        RED = (0.5, 0, 0)  # игрок 2
        scaleX = 2135
        scaleY = 615
        sizeScale = 24
        shiftX = 35 / 2100
        shiftY = 16 / 500
        coordins = []
        for hexagon in xy:
            hexagon = int(hexagon[0]), int(hexagon[1])
            x, y = self.computeCoordinates(hexagon)
            coordins.append([x / scaleX + shiftX, y / scaleY + shiftY])
            if self.state_matrix[hexagon][self.general_dict["black"]] == 1:
                color.append(BLACK)
            if self.state_matrix[hexagon][self.P1_dict["player_hexes"]] == 1:
                color.append(BLUE)
            if self.state_matrix[hexagon][self.P2_dict["player_hexes"]] == 1:
                color.append(RED)
            if self.state_matrix[hexagon][self.general_dict["gray"]] == 1:
                color.append(GRAY)
            if self.state_matrix[hexagon][self.general_dict["pine"]] == 1:
                entity_distribution["pine"].append(hexagon)
            if self.state_matrix[hexagon][self.general_dict["palm"]] == 1:
                entity_distribution["palm"].append(hexagon)
            if self.unit_type[hexagon] != 0:
                unit = "unit" + str(self.unit_type[hexagon])
                entity_distribution[unit].append(hexagon)
            if self.state_matrix[hexagon][self.general_dict["graves"]] == 1:
                entity_distribution["grave"].append(hexagon)
            if (
                self.state_matrix[hexagon][self.P1_dict["tower1"]] == 1
                or self.state_matrix[hexagon][self.P2_dict["tower1"]] == 1
            ):
                entity_distribution["tower1"].append(hexagon)
            if (
                self.state_matrix[hexagon][self.P1_dict["ambar"]] == 1
                or self.state_matrix[hexagon][self.P2_dict["ambar"]] == 1
            ):
                entity_distribution["ambar"].append(hexagon)
            if (
                self.state_matrix[hexagon][self.P1_dict["tower2"]] == 1
                or self.state_matrix[hexagon][self.P2_dict["tower2"]] == 1
            ):
                entity_distribution["tower2"].append(hexagon)
            if (
                self.state_matrix[hexagon][self.P1_dict["town"]] == 1
                or self.state_matrix[hexagon][self.P2_dict["town"]] == 1
            ):
                entity_distribution["town"].append(hexagon)

        col = collections.RegularPolyCollection(
            6,
            rotation=0,
            sizes=((np.pi * self.r**2) / sizeScale,),
            offsets=coordins,
            transOffset=ax.transData,
        )

        ax.add_collection(col, autolim=True)
        col.set_color(color)

        for entity, hex_list in entity_distribution.items():
            for hexagon in hex_list:
                x, y = self.computeCoordinates(hexagon)
                x -= self.r / 10
                y += self.r / 10
                new_ax = fig.add_axes(
                    [x / picture_width, y / picture_height, hex_size, hex_size],
                    zorder=2,
                )
                new_ax.axis("off")
                new_ax.imshow(pictures[entity])

        fig.savefig(plot_save_path)
