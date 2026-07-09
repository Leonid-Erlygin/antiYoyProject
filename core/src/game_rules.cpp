#include "game_rules.hpp"

#include <algorithm>
#include <cassert>
#include <deque>
#include <map>
#include <set>
#include <stdexcept>
#include <unordered_set>

namespace hexgame {

namespace {
template <typename T>
void removeValue(std::vector<T>& v, const T& value) {
    v.erase(std::remove(v.begin(), v.end(), value), v.end());
}
template <typename T>
bool contains(const std::vector<T>& v, const T& value) {
    return std::find(v.begin(), v.end(), value) != v.end();
}
}  // namespace

// ==========================================================================
// Province money / income
// ==========================================================================
void GameRules::changeMoneyInProvince(int provinceIndex, int newMoney,
                                      bool adversary) {
    auto& provinces = adversary ? gs_.adversaryProvinces() : gs_.activeProvinces();
    const int p = adversary ? gs_.adversaryPlane(plane::kMoney)
                            : gs_.activePlane(plane::kMoney);
    auto it = provinces.find(provinceIndex);
    if (it == provinces.end()) return;
    for (const Hex& h : it->second.hexes) gs_.at(h, p) = newMoney;
}

void GameRules::changeIncomeInProvince(int provinceIndex, int newIncome,
                                       bool adversary) {
    auto& provinces = adversary ? gs_.adversaryProvinces() : gs_.activeProvinces();
    const int p = adversary ? gs_.adversaryPlane(plane::kIncome)
                            : gs_.activePlane(plane::kIncome);
    auto it = provinces.find(provinceIndex);
    if (it == provinces.end()) return;
    for (const Hex& h : it->second.hexes) gs_.at(h, p) = newIncome;
}

// ==========================================================================
// Defence
// ==========================================================================
int GameRules::enemyBuilding(const Hex& h) const {
    if (gs_.at(h, gs_.adversaryPlane(plane::kTown)) == 1) return 1;
    if (gs_.at(h, gs_.adversaryPlane(plane::kTower1)) == 1) return 2;
    if (gs_.at(h, gs_.adversaryPlane(plane::kTower2)) == 1) return 3;
    return 0;
}

int GameRules::enemyHexDefence(const Hex& hexagon) const {
    int power = 0;
    for (int d = 0; d < 6; ++d) {
        auto adj = gs_.geometry().adjacent(hexagon, d);
        if (!adj) continue;
        if (gs_.at(*adj, gs_.adversaryPlane(plane::kPlayerHexes)) == 0) continue;
        power = std::max({power, static_cast<int>(gs_.unitType(*adj)),
                          enemyBuilding(*adj)});
    }
    return std::max({power, static_cast<int>(gs_.unitType(hexagon)),
                     enemyBuilding(hexagon)});
}

// ==========================================================================
// Connectivity BFS (movement range)
// ==========================================================================
std::vector<Hex> GameRules::bfsConnectivity(const Hex& origin) const {
    const int steps = gs_.config().moveSize;
    std::deque<std::pair<Hex, int>> queue;
    std::vector<Hex> reachable;
    std::unordered_set<int> reached;
    const auto& geo = gs_.geometry();

    queue.emplace_back(origin, steps);
    reached.insert(geo.index(origin));
    reachable.push_back(origin);

    while (!queue.empty()) {
        auto [h, step] = queue.front();
        queue.pop_front();
        if (step == 0) continue;
        for (int d = 0; d < 6; ++d) {
            auto adj = geo.adjacent(h, d);
            if (!adj) continue;
            if (reached.count(geo.index(*adj))) continue;
            if (gs_.at(*adj, plane::kBlack) == 1) continue;
            reached.insert(geo.index(*adj));
            reachable.push_back(*adj);
            // continue BFS only through friendly hexes
            if (gs_.at(*adj, gs_.activePlane(plane::kPlayerHexes)) == 1)
                queue.emplace_back(*adj, step - 1);
        }
    }
    return reachable;
}

// ==========================================================================
// Legality masks
// ==========================================================================
std::vector<Hex> GameRules::hexesWithFriendlyUnits() const {
    std::vector<Hex> out;
    for (const Hex& h : gs_.activeUnits()) {
        if (gs_.at(h, gs_.activePlane(plane::kPlayerHexes)) == 1 &&
            gs_.unitType(h) != 0) {
            out.push_back(h);
        }
    }
    return out;
}

std::vector<uint8_t> GameRules::legalUnitMoves(const Hex& hexagon) const {
    const int n = gs_.config().numMoveTargets();
    const int stay = gs_.config().stayIndex();
    std::vector<uint8_t> mask(n, 0);

    const int unitType = gs_.unitType(hexagon);
    if (unitType == 0) return mask;

    std::unordered_set<int> reachable;
    for (const Hex& h : bfsConnectivity(hexagon))
        reachable.insert(gs_.geometry().index(h));

    bool any = false;
    for (int i = 0; i < n; ++i) {
        if (i == stay) continue;
        auto target = gs_.geometry().hexByLayer(i, hexagon, n);
        if (!target) continue;
        const Hex t = *target;
        if (!reachable.count(gs_.geometry().index(t))) continue;
        // cannot enter our own hex with a building
        if (gs_.at(t, gs_.activePlane(plane::kPlayerHexes)) == 1 &&
            (gs_.at(t, gs_.activePlane(plane::kAmbar)) == 1 ||
             gs_.at(t, gs_.activePlane(plane::kTower1)) == 1 ||
             gs_.at(t, gs_.activePlane(plane::kTower2)) == 1 ||
             gs_.at(t, gs_.activePlane(plane::kTown)) == 1)) {
            continue;
        }
        // friendly-unit merge constraint
        if (gs_.at(t, gs_.activePlane(plane::kPlayerHexes)) == 1) {
            const int friendly = gs_.unitType(t);
            if (friendly != 0 && unitType + friendly > 4) continue;
        }
        // enemy hex defence
        if (gs_.at(t, gs_.adversaryPlane(plane::kPlayerHexes)) == 1) {
            if (unitType <= enemyHexDefence(t)) continue;
        }
        mask[i] = 1;
        any = true;
    }
    if (!any) mask[stay] = 1;  // must be able to stay
    else mask[stay] = 1;       // staying is always allowed
    return mask;
}

GameRules::SpendLegality GameRules::legalSpends(const Hex& hexagon) const {
    SpendLegality res;
    res.spendHex = hexagon;
    static constexpr std::array<int, 6> kPrices = {10, 20, 30, 15, 35, 40};

    auto nothingOnly = [&res]() {
        res.mask.fill(0);
        res.mask[kSpendNothing] = 1;
    };

    if (gs_.at(hexagon, plane::kBlack) == 1) {
        nothingOnly();
        return res;
    }

    if (gs_.at(hexagon, gs_.activePlane(plane::kPlayerHexes)) == 1) {
        // ---- own hex ----
        const int province = gs_.at(hexagon, gs_.activePlane(plane::kProvinceIndex));
        const auto& provinces = gs_.activeProvinces();
        auto pit = provinces.find(province);
        if (pit == provinces.end()) {  // isolated single hex
            nothingOnly();
            return res;
        }
        // hard-blocked cells
        if (gs_.at(hexagon, gs_.activePlane(plane::kTower2)) == 1 ||
            gs_.at(hexagon, gs_.activePlane(plane::kTown)) == 1 ||
            gs_.at(hexagon, gs_.activePlane(plane::kAmbar)) == 1 ||
            gs_.at(hexagon, gs_.activePlane(plane::kUnit4)) == 1) {
            nothingOnly();
            return res;
        }
        const int money = gs_.at(hexagon, gs_.activePlane(plane::kMoney));

        if (gs_.unitType(hexagon) != 0) {
            // upgrading a unit on the spot
            for (int u = 0; u < 3; ++u) {
                const bool accepted = (u + 1) + gs_.unitType(hexagon) <= 4;
                const bool affordable = kPrices[u] <= money;
                res.mask[u] = accepted && affordable;
            }
            res.mask[kSpendNothing] = 1;
            return res;
        }
        if (gs_.at(hexagon, gs_.activePlane(plane::kTower1)) == 1) {
            if (money >= 35) res.mask[4] = 1;  // upgrade to big tower
            res.mask[kSpendNothing] = 1;
            return res;
        }
        if (gs_.at(hexagon, plane::kPine) == 1) {
            // no buildings on a tree; units allowed
            for (int u = 0; u < 3; ++u) res.mask[u] = kPrices[u] <= money;
            res.mask[5] = money >= 40;
            res.mask[kSpendNothing] = 1;
            return res;
        }
        // empty own cell
        for (int a = 0; a < 6; ++a) res.mask[a] = kPrices[a] <= money;
        // barn: adjacency to barn/town + price
        const int ambarCost = pit->second.ambarCost;
        bool nearAmbar = false;
        if (ambarCost <= money) {
            for (int d = 0; d < 6; ++d) {
                if (auto adj = gs_.geometry().adjacent(hexagon, d)) {
                    if (gs_.at(*adj, gs_.activePlane(plane::kAmbar)) == 1 ||
                        gs_.at(*adj, gs_.activePlane(plane::kTown)) == 1) {
                        nearAmbar = true;
                        break;
                    }
                }
            }
        }
        res.mask[6] = (ambarCost <= money) && nearAmbar;
        res.mask[kSpendNothing] = 1;
        return res;
    }

    // ---- gray or enemy hex: needs an adjacent friendly province ----
    Hex bestProvinceHex(-1, -1);
    int bestMoney = INT32_MIN;
    for (int d = 0; d < 6; ++d) {
        if (auto adj = gs_.geometry().adjacent(hexagon, d)) {
            const int prov = gs_.at(*adj, gs_.activePlane(plane::kProvinceIndex));
            if (prov != 0) {
                const int m = gs_.at(*adj, gs_.activePlane(plane::kMoney));
                if (m > bestMoney) {
                    bestMoney = m;
                    bestProvinceHex = *adj;
                }
            }
        }
    }
    if (!bestProvinceHex.valid()) {
        nothingOnly();
        return res;
    }
    res.spendHex = bestProvinceHex;
    const int money = bestMoney;

    if (gs_.at(hexagon, plane::kGray) == 1) {
        for (int u = 0; u < 3; ++u) res.mask[u] = kPrices[u] <= money;
        res.mask[5] = money >= 40;
    } else if (gs_.at(hexagon, gs_.adversaryPlane(plane::kPlayerHexes)) == 1) {
        const int defence = enemyHexDefence(hexagon);
        for (int u = 0; u < 3; ++u)
            res.mask[u] = (kPrices[u] <= money) && ((u + 1) > defence);
        res.mask[5] = (money >= 40) && (4 > defence);
    } else {
        nothingOnly();
        return res;
    }
    res.mask[kSpendNothing] = 1;
    return res;
}

// ==========================================================================
// updateBeforeMove — starvation, income, graves -> trees
// ==========================================================================
void GameRules::updateBeforeMove() {
    std::vector<std::pair<int, int>> provinceCasualties;  // (province, unitType)
    std::vector<Hex> newGraves;
    std::set<int> nullProvinces;
    std::vector<Hex> removeList;

    auto allUnits = gs_.activeUnits();
    for (const Hex& u : gs_.adversaryUnits()) allUnits.push_back(u);

    for (const Hex& unitHex : allUnits) {
        if (gs_.at(unitHex, gs_.activePlane(plane::kPlayerHexes)) == 0 ||
            gs_.at(unitHex, gs_.activePlane(plane::kProvinceIndex)) == 0) {
            continue;
        }
        const int money = gs_.at(unitHex, gs_.activePlane(plane::kMoney));
        const int income = gs_.at(unitHex, gs_.activePlane(plane::kIncome));
        if (money + income < 0) {
            const int province =
                gs_.at(unitHex, gs_.activePlane(plane::kProvinceIndex));
            changeMoneyInProvince(province, 0, /*adversary=*/false);
            nullProvinces.insert(province);
            provinceCasualties.emplace_back(province, gs_.unitType(unitHex));
            gs_.at(unitHex,
                   gs_.activePlane(plane::kUnit1 + gs_.unitType(unitHex) - 1)) = 0;
            gs_.setUnitType(unitHex, 0);
            removeList.push_back(unitHex);
            gs_.at(unitHex, plane::kGraves) = 1;
            newGraves.push_back(unitHex);
        }
    }
    for (const Hex& h : removeList) {
        removeValue(gs_.activeUnits(), h);
        removeValue(gs_.adversaryUnits(), h);
    }

    // kill units stranded on single cells (dead_hexes)
    for (const Hex& h : gs_.deadHexes()) {
        const int ut = gs_.unitType(h);
        if (ut == 0) continue;
        // the unit belongs to whichever player owns the hex
        if (gs_.at(h, gs_.activePlane(plane::kPlayerHexes)) == 1) {
            gs_.at(h, gs_.activePlane(plane::kUnit1 + ut - 1)) = 0;
            removeValue(gs_.activeUnits(), h);
        } else {
            gs_.at(h, gs_.adversaryPlane(plane::kUnit1 + ut - 1)) = 0;
            removeValue(gs_.adversaryUnits(), h);
        }
        gs_.at(h, plane::kGraves) = 1;
        newGraves.push_back(h);
        gs_.setUnitType(h, 0);
    }
    gs_.deadHexes().clear();

    // income gain from casualties
    std::map<int, int> provinceGain;
    for (auto [province, ut] : provinceCasualties) provinceGain[province] -= unitFood(ut);
    for (auto& [province, gain] : provinceGain) {
        auto it = gs_.activeProvinces().find(province);
        if (it == gs_.activeProvinces().end() || it->second.hexes.empty()) continue;
        const int cur = gs_.at(it->second.hexes.front(), gs_.activePlane(plane::kIncome));
        changeIncomeInProvince(province, cur + gain, false);
    }

    // accrue income for surviving provinces
    for (auto& [province, prov] : gs_.activeProvinces()) {
        if (nullProvinces.count(province)) continue;
        if (prov.hexes.empty()) continue;
        const Hex sample = prov.hexes.front();
        const int money = gs_.at(sample, gs_.activePlane(plane::kMoney));
        const int income = gs_.at(sample, gs_.activePlane(plane::kIncome));
        if (money == 0 && income <= 0) continue;
        if (money + income < 0) {
            changeMoneyInProvince(province, 0, false);
        } else {
            changeMoneyInProvince(province, money + income, false);
        }
    }

    // active player's old graves become trees
    std::vector<Hex> gravesToRemove;
    std::map<int, int> provinceLoss;
    for (const Hex& grave : gs_.graveList()) {
        const int gravePlayer =
            gs_.at(grave, gs_.activePlane(plane::kPlayerHexes)) == 1 ? gs_.activePlayer()
                                                                     : 1 - gs_.activePlayer();
        if (gs_.activePlayer() == gravePlayer) {
            gs_.at(grave, plane::kGraves) = 0;
            gravesToRemove.push_back(grave);
            gs_.at(grave, plane::kPine) = 1;
            gs_.treeList().push_back(grave);
            const int province = gs_.at(grave, gs_.activePlane(plane::kProvinceIndex));
            if (province != 0) ++provinceLoss[province];
        }
    }
    auto& graves = gs_.graveList();
    for (const Hex& g : gravesToRemove) removeValue(graves, g);
    for (const Hex& g : newGraves) graves.push_back(g);

    for (auto& [province, loss] : provinceLoss) {
        auto it = gs_.activeProvinces().find(province);
        if (it == gs_.activeProvinces().end() || it->second.hexes.empty()) continue;
        const int cur = gs_.at(it->second.hexes.front(), gs_.activePlane(plane::kIncome));
        changeIncomeInProvince(province, cur - loss, false);
    }
}

// ==========================================================================
// updateAfterMove — tree growth
// ==========================================================================
void GameRules::updateAfterMove() {
    const double p = gs_.config().treeGrowthProbability;
    std::uniform_real_distribution<double> uni(0.0, 1.0);
    std::map<int, int> activeLoss, adversaryLoss;

    const auto treesSnapshot = gs_.treeList();
    for (const Hex& tree : treesSnapshot) {
        if (uni(gs_.rng()) >= p) continue;
        std::vector<Hex> valid;
        for (int d = 0; d < 6; ++d) {
            if (auto adj = gs_.geometry().adjacent(tree, d)) {
                if (gs_.at(*adj, plane::kBlack) == 0 && gs_.unitType(*adj) == 0 &&
                    gs_.at(*adj, plane::kPine) == 0) {
                    valid.push_back(*adj);
                }
            }
        }
        if (valid.empty()) continue;
        std::uniform_int_distribution<size_t> pick(0, valid.size() - 1);
        const Hex newTree = valid[pick(gs_.rng())];
        gs_.at(newTree, plane::kPine) = 1;
        gs_.treeList().push_back(newTree);
        const int p1 = gs_.at(newTree, gs_.activePlane(plane::kProvinceIndex));
        const int p2 = gs_.at(newTree, gs_.adversaryPlane(plane::kProvinceIndex));
        if (p1 != 0) ++activeLoss[p1];
        else if (p2 != 0) ++adversaryLoss[p2];
    }
    for (auto& [province, loss] : activeLoss) {
        auto it = gs_.activeProvinces().find(province);
        if (it == gs_.activeProvinces().end() || it->second.hexes.empty()) continue;
        const int cur = gs_.at(it->second.hexes.front(), gs_.activePlane(plane::kIncome));
        changeIncomeInProvince(province, cur - loss, false);
    }
    for (auto& [province, loss] : adversaryLoss) {
        auto it = gs_.adversaryProvinces().find(province);
        if (it == gs_.adversaryProvinces().end() || it->second.hexes.empty()) continue;
        const int cur =
            gs_.at(it->second.hexes.front(), gs_.adversaryPlane(plane::kIncome));
        changeIncomeInProvince(province, cur - loss, true);
    }
}

// ==========================================================================
// Province detection / merge / split — unit_move.py
// ==========================================================================
GameRules::DetectedProvince GameRules::detectProvince(const Hex& hexagon,
                                                      bool adversary,
                                                      int newProvinceIndex) {
    DetectedProvince result;
    const int hexPlane = adversary ? gs_.adversaryPlane(plane::kPlayerHexes)
                                   : gs_.activePlane(plane::kPlayerHexes);
    const int provPlane = adversary ? gs_.adversaryPlane(plane::kProvinceIndex)
                                    : gs_.activePlane(plane::kProvinceIndex);
    const int t1 = adversary ? gs_.adversaryPlane(plane::kTower1)
                             : gs_.activePlane(plane::kTower1);
    const int t2 = adversary ? gs_.adversaryPlane(plane::kTower2)
                             : gs_.activePlane(plane::kTower2);
    const int amb = adversary ? gs_.adversaryPlane(plane::kAmbar)
                              : gs_.activePlane(plane::kAmbar);
    const int town = adversary ? gs_.adversaryPlane(plane::kTown)
                               : gs_.activePlane(plane::kTown);

    std::deque<Hex> queue;
    std::vector<uint8_t> reached(gs_.geometry().numCells(), 0);
    queue.push_back(hexagon);
    result.hexes.push_back(hexagon);
    reached[gs_.geometry().index(hexagon)] = 1;
    if (newProvinceIndex != 0) gs_.at(hexagon, provPlane) = newProvinceIndex;

    int totalIncome = 0;
    while (!queue.empty()) {
        const Hex h = queue.front();
        queue.pop_front();
        if (gs_.unitType(h) != 0) {
            totalIncome += unitFood(gs_.unitType(h));
        } else if (gs_.at(h, t1) == 1) {
            totalIncome += -1;
        } else if (gs_.at(h, t2) == 1) {
            totalIncome += -6;
        } else if (gs_.at(h, amb) == 1) {
            ++result.numBarns;
            totalIncome += 4;
        } else if (gs_.at(h, plane::kPine) == 1) {
            totalIncome += -1;
        } else if (gs_.at(h, town) == 1) {
            result.hasTown = true;
        }
        for (int d = 0; d < 6; ++d) {
            if (auto adj = gs_.geometry().adjacent(h, d)) {
                if (!reached[gs_.geometry().index(*adj)] &&
                    gs_.at(*adj, hexPlane) == 1) {
                    result.hexes.push_back(*adj);
                    if (newProvinceIndex != 0)
                        gs_.at(*adj, provPlane) = newProvinceIndex;
                    queue.push_back(*adj);
                    reached[gs_.geometry().index(*adj)] = 1;
                }
            }
        }
    }
    result.income = totalIncome + static_cast<int>(result.hexes.size());
    return result;
}

void GameRules::mergeProvinces(const std::vector<int>& provincesToMerge,
                               const Hex& junctionHex) {
    auto& provinces = gs_.activeProvinces();
    const int minIndex = *std::min_element(provincesToMerge.begin(),
                                           provincesToMerge.end());
    std::vector<Hex> newList;
    int sumMoney = 0, sumIncome = 0, numAmbars = 0;

    for (int p : provincesToMerge) {
        auto it = provinces.find(p);
        if (it == provinces.end() || it->second.hexes.empty()) continue;
        const Hex sample = it->second.hexes.front();
        sumMoney += gs_.at(sample, gs_.activePlane(plane::kMoney));
        sumIncome += gs_.at(sample, gs_.activePlane(plane::kIncome));
        for (const Hex& h : it->second.hexes) newList.push_back(h);
        numAmbars += (it->second.ambarCost - 12) / 2;
        provinces.erase(it);
    }
    sumIncome += 1;  // the junction hex
    newList.push_back(junctionHex);
    gs_.at(junctionHex, gs_.activePlane(plane::kPlayerHexes)) = 1;

    bool firstTown = true;
    for (const Hex& h : newList) {
        gs_.at(h, gs_.activePlane(plane::kMoney)) = sumMoney;
        gs_.at(h, gs_.activePlane(plane::kIncome)) = sumIncome;
        gs_.at(h, gs_.activePlane(plane::kProvinceIndex)) = minIndex;
        if (gs_.at(h, gs_.activePlane(plane::kTown)) == 1) {
            if (firstTown) firstTown = false;
            else gs_.at(h, gs_.activePlane(plane::kTown)) = 0;
        }
    }
    Province merged;
    merged.hexes = std::move(newList);
    merged.ambarCost = 12 + 2 * numAmbars;
    provinces[minIndex] = std::move(merged);
}

Hex GameRules::findPlaceForNewTown(int provinceIndex) {
    auto& provinces = gs_.adversaryProvinces();
    auto it = provinces.find(provinceIndex);
    assert(it != provinces.end());
    Province& province = it->second;

    for (const Hex& h : province.hexes) {
        if (gs_.unitType(h) != 0) continue;
        if (gs_.at(h, gs_.adversaryPlane(plane::kTower1)) == 0 &&
            gs_.at(h, gs_.adversaryPlane(plane::kTower2)) == 0 &&
            gs_.at(h, gs_.adversaryPlane(plane::kAmbar)) == 0 &&
            gs_.at(h, plane::kGraves) == 0 && gs_.at(h, plane::kPine) == 0) {
            return h;
        }
    }
    // no clean spot — take the first non-barn hex, otherwise destroy a barn
    Hex toDelete(-1, -1);
    for (const Hex& h : province.hexes) {
        if (gs_.at(h, gs_.adversaryPlane(plane::kAmbar)) == 0) {
            toDelete = h;
            break;
        }
    }
    if (!toDelete.valid()) {
        std::uniform_int_distribution<size_t> pick(0, province.hexes.size() - 1);
        const Hex h = province.hexes[pick(gs_.rng())];
        const int cur = gs_.at(h, gs_.adversaryPlane(plane::kIncome));
        changeIncomeInProvince(provinceIndex, cur - 4, true);
        province.ambarCost -= 2;
        gs_.at(h, gs_.adversaryPlane(plane::kAmbar)) = 0;
        return h;
    }
    int gain = 0;
    if (gs_.unitType(toDelete) != 0) {
        const int ut = gs_.unitType(toDelete);
        gain = -unitFood(ut);
        gs_.setUnitType(toDelete, 0);
        gs_.at(toDelete, gs_.adversaryPlane(plane::kUnit1 + ut - 1)) = 0;
        removeValue(gs_.adversaryUnits(), toDelete);
    } else if (gs_.at(toDelete, gs_.adversaryPlane(plane::kTower1)) == 1) {
        gain = 1;
        gs_.at(toDelete, gs_.adversaryPlane(plane::kTower1)) = 0;
    } else if (gs_.at(toDelete, gs_.adversaryPlane(plane::kTower2)) == 1) {
        gs_.at(toDelete, gs_.adversaryPlane(plane::kTower2)) = 0;
        gain = 6;
    } else if (gs_.at(toDelete, plane::kGraves) == 1) {
        removeValue(gs_.graveList(), toDelete);
        gs_.at(toDelete, plane::kGraves) = 0;
    } else if (gs_.at(toDelete, plane::kPine) == 1) {
        removeValue(gs_.treeList(), toDelete);
        gain = 1;
        gs_.at(toDelete, plane::kPine) = 0;
    }
    const int cur = gs_.at(toDelete, gs_.adversaryPlane(plane::kIncome));
    changeIncomeInProvince(provinceIndex, cur + gain, true);
    return toDelete;
}

// ==========================================================================
// performOneUnitMove — full port of unit_move.py
// ==========================================================================
void GameRules::performOneUnitMove(const Hex& departure, const Hex& destination,
                                   int unitType) {
    auto activeP = [this](int rel) { return gs_.activePlane(rel); };
    auto advP = [this](int rel) { return gs_.adversaryPlane(rel); };

    if (gs_.at(destination, plane::kGraves) == 1) {
        gs_.at(destination, plane::kGraves) = 0;
        removeValue(gs_.graveList(), destination);
    }

    if (gs_.at(destination, activeP(plane::kPlayerHexes)) == 1) {
        // -------- moving inside own territory --------
        if (gs_.at(destination, plane::kPine) == 1) {
            gs_.at(destination, plane::kPine) = 0;
            removeValue(gs_.treeList(), destination);
            gs_.at(destination, activeP(plane::kUnit1 + unitType - 1)) = 1;
            gs_.setUnitType(destination, static_cast<uint8_t>(unitType));
            const int province =
                gs_.at(destination, activeP(plane::kProvinceIndex));
            changeMoneyInProvince(
                province, gs_.at(destination, activeP(plane::kMoney)) + 3, false);
            changeIncomeInProvince(
                province, gs_.at(destination, activeP(plane::kIncome)) + 1, false);
        } else if (gs_.unitType(destination) != 0) {
            // merging friendly units
            const int destUnit = gs_.unitType(destination);
            gs_.at(destination, activeP(plane::kUnit1 + destUnit + unitType - 1)) = 1;
            int reduceIncome = 0;
            if (unitType == 1 && destUnit == 1) reduceIncome = -2;
            if ((unitType == 1 && destUnit == 2) || (unitType == 2 && destUnit == 1))
                reduceIncome = -10;
            if ((unitType == 1 && destUnit == 3) || (unitType == 3 && destUnit == 1))
                reduceIncome = -16;
            if (unitType == 2 && destUnit == 2) reduceIncome = -24;
            changeIncomeInProvince(
                gs_.at(destination, activeP(plane::kProvinceIndex)),
                gs_.at(destination, activeP(plane::kIncome)) + reduceIncome, false);
            gs_.setUnitType(destination,
                            static_cast<uint8_t>(destUnit + unitType));
        } else {
            gs_.setUnitType(destination, static_cast<uint8_t>(unitType));
            gs_.at(destination, activeP(plane::kUnit1 + unitType - 1)) = 1;
        }
        return;
    }

    // -------- expanding into gray / enemy territory --------
    gs_.setLastExpandedStep(gs_.activePlayer(), gs_.step());

    const int destinationHexProvince =
        gs_.at(destination, advP(plane::kProvinceIndex));

    auto& provinces = gs_.activeProvinces();
    std::vector<Hex> adjacentHexes = gs_.adjacentFriendlyHexes(destination, false);
    std::vector<int> adjacentProvinces;
    for (const Hex& h : adjacentHexes) {
        int province = gs_.at(h, activeP(plane::kProvinceIndex));
        if (std::find(adjacentProvinces.begin(), adjacentProvinces.end(), province) ==
            adjacentProvinces.end()) {
            if (province == 0) {
                // single friendly hex — create a fictive province
                int newKey = provinces.empty() ? 1 : provinces.rbegin()->first + 1;
                province = newKey;
                Province p;
                p.hexes = {h};
                p.ambarCost = 12;
                provinces[newKey] = std::move(p);
                int income = gs_.at(h, plane::kPine) == 1 ? 0 : 1;
                gs_.at(h, activeP(plane::kIncome)) = income;
                gs_.at(h, activeP(plane::kProvinceIndex)) = newKey;
            }
            adjacentProvinces.push_back(province);
        }
    }

    if (adjacentProvinces.size() == 1) {
        gs_.at(destination, activeP(plane::kPlayerHexes)) = 1;
        // find a hex of that province to copy money from
        const int province = adjacentProvinces[0];
        Hex sample = provinces[province].hexes.front();
        gs_.at(destination, activeP(plane::kMoney)) =
            gs_.at(sample, activeP(plane::kMoney));
        provinces[province].hexes.push_back(destination);
        changeIncomeInProvince(province,
                               gs_.at(sample, activeP(plane::kIncome)) + 1, false);
        gs_.at(destination, activeP(plane::kProvinceIndex)) = province;
    } else if (adjacentProvinces.size() > 1) {
        mergeProvinces(adjacentProvinces, destination);
    } else {
        throw std::runtime_error(
            "performOneUnitMove: no adjacent provinces detected");
    }
    gs_.at(destination, activeP(plane::kUnit1 + unitType - 1)) = 1;

    if (gs_.at(destination, plane::kGray) == 1) {
        // capture a gray hex
        if (gs_.at(destination, plane::kPine) == 1) {
            removeValue(gs_.treeList(), destination);
            gs_.at(destination, plane::kPine) = 0;
        }
        gs_.at(destination, plane::kGray) = 0;
        gs_.setUnitType(destination, static_cast<uint8_t>(unitType));
        return;
    }

    // ---- capturing an enemy hex; provinces might split ----
    std::vector<Hex> rootsOfPossibleProvinces;
    std::vector<Hex> Ax = gs_.adjacentFriendlyHexes(destination, true);
    int grayDirection = -1;
    for (int d = 0; d < 6; ++d) {
        auto adj = gs_.geometry().adjacent(destination, d);
        if (!adj || !contains(Ax, *adj)) {
            grayDirection = d;
            break;
        }
    }
    if (grayDirection < 0) grayDirection = 0;
    bool hasNear = false;
    for (int i = 0; i < 6; ++i) {
        auto adj = gs_.geometry().adjacent(destination, (grayDirection + i) % 6);
        const bool inAx = adj && contains(Ax, *adj);
        if (inAx && !hasNear) {
            rootsOfPossibleProvinces.push_back(*adj);
            hasNear = true;
        }
        if (!inAx) hasNear = false;
    }

    std::vector<Hex> actualRoots;
    std::map<int, DetectedProvince> newDetected;  // key = index into actualRoots

    gs_.at(destination, advP(plane::kPlayerHexes)) = 0;
    gs_.at(destination, advP(plane::kProvinceIndex)) = 0;
    gs_.at(destination, advP(plane::kIncome)) = 0;

    if (rootsOfPossibleProvinces.size() > 1) {
        std::vector<Hex> pending = rootsOfPossibleProvinces;
        while (!pending.empty()) {
            Hex root = pending.back();
            pending.pop_back();
            DetectedProvince dp = detectProvince(root, true, 0);
            std::vector<Hex> stillPending;
            for (const Hex& v : pending)
                if (!contains(dp.hexes, v)) stillPending.push_back(v);
            pending = std::move(stillPending);
            newDetected[static_cast<int>(actualRoots.size())] = std::move(dp);
            actualRoots.push_back(root);
        }
    } else {
        actualRoots = rootsOfPossibleProvinces;
    }

    auto& advProvinces = gs_.adversaryProvinces();
    const int province = destinationHexProvince;

    if (actualRoots.size() <= 1) {
        gs_.at(destination, advP(plane::kMoney)) = 0;

        if (!actualRoots.empty()) {
            auto it = advProvinces.find(province);
            if (it != advProvinces.end())
                removeValue(it->second.hexes, destination);
        }
        auto it = advProvinces.find(province);

        if (!actualRoots.empty() && it != advProvinces.end() &&
            it->second.hexes.size() == 1) {
            // province of two cells collapses
            const Hex remainder = it->second.hexes.front();
            if (gs_.at(destination, advP(plane::kTown)) == 1) {
                gs_.at(destination, advP(plane::kTown)) = 0;
                gs_.at(remainder, advP(plane::kAmbar)) = 0;
                gs_.at(remainder, advP(plane::kTower1)) = 0;
                gs_.at(remainder, advP(plane::kTower2)) = 0;
                gs_.at(remainder, advP(plane::kProvinceIndex)) = 0;
                if (gs_.unitType(remainder) != 0)
                    gs_.deadHexes().push_back(remainder);
            } else {
                gs_.at(remainder, advP(plane::kTown)) = 0;
                gs_.at(destination, advP(plane::kAmbar)) = 0;
                gs_.at(destination, advP(plane::kTower1)) = 0;
                gs_.at(destination, advP(plane::kTower2)) = 0;
                if (gs_.at(destination, plane::kPine) == 1) {
                    removeValue(gs_.treeList(), destination);
                    gs_.at(destination, plane::kPine) = 0;
                }
                const int advUnit = gs_.unitType(destination);
                if (advUnit != 0) {
                    gs_.at(destination, advP(plane::kUnit1 + advUnit - 1)) = 0;
                    removeValue(gs_.adversaryUnits(), destination);
                }
                gs_.at(remainder, plane::kPine) = 1;
                gs_.treeList().push_back(remainder);
                gs_.at(remainder, advP(plane::kProvinceIndex)) = 0;
            }
            gs_.at(remainder, advP(plane::kMoney)) = 0;
            gs_.at(remainder, advP(plane::kIncome)) = 0;
            advProvinces.erase(province);
        } else if (!actualRoots.empty() && it != advProvinces.end()) {
            // enemy province simply lost one cell
            const int advUnit = gs_.unitType(destination);
            int gain = 0;
            if (advUnit != 0) {
                gs_.at(destination, advP(plane::kUnit1 + advUnit - 1)) = 0;
                removeValue(gs_.adversaryUnits(), destination);
                gain = -unitFood(advUnit);
            } else if (gs_.at(destination, advP(plane::kTower1)) == 1) {
                gs_.at(destination, advP(plane::kTower1)) = 0;
                gain = 1;
            } else if (gs_.at(destination, advP(plane::kTower2)) == 1) {
                gs_.at(destination, advP(plane::kTower2)) = 0;
                gain = 6;
            } else if (gs_.at(destination, advP(plane::kAmbar)) == 1) {
                it->second.ambarCost -= 2;
                gs_.at(destination, advP(plane::kAmbar)) = 0;
                gain = -4;
            } else if (gs_.at(destination, plane::kPine) == 1) {
                removeValue(gs_.treeList(), destination);
                gs_.at(destination, plane::kPine) = 0;
                gain = 1;
            } else if (gs_.at(destination, advP(plane::kTown)) == 1) {
                gs_.at(destination, advP(plane::kTown)) = 0;
                const Hex place = findPlaceForNewTown(province);
                gs_.at(place, advP(plane::kTown)) = 1;
            }
            const int cur =
                gs_.at(it->second.hexes.front(), advP(plane::kIncome));
            changeIncomeInProvince(province, cur + gain - 1, true);
        } else {
            // stray enemy hex (no province) — just clean up trees
            if (gs_.at(destination, plane::kPine) == 1) {
                removeValue(gs_.treeList(), destination);
                gs_.at(destination, plane::kPine) = 0;
            }
            const int advUnit = gs_.unitType(destination);
            if (advUnit != 0) {
                gs_.at(destination, advP(plane::kUnit1 + advUnit - 1)) = 0;
                removeValue(gs_.adversaryUnits(), destination);
            }
            gs_.at(destination, advP(plane::kTown)) = 0;
            gs_.at(destination, advP(plane::kTower1)) = 0;
            gs_.at(destination, advP(plane::kTower2)) = 0;
            gs_.at(destination, advP(plane::kAmbar)) = 0;
        }
        gs_.setUnitType(destination, static_cast<uint8_t>(unitType));
        return;
    }

    // ---- the enemy province splits into several ----
    int oldMoney = 0;
    {
        auto it = advProvinces.find(province);
        if (it != advProvinces.end() && !it->second.hexes.empty()) {
            oldMoney = gs_.at(it->second.hexes.front(), advP(plane::kMoney));
        }
        advProvinces.erase(province);
    }

    // clean junction hex
    if (gs_.unitType(destination) != 0) {
        gs_.at(destination, advP(plane::kUnit1 + gs_.unitType(destination) - 1)) = 0;
        removeValue(gs_.adversaryUnits(), destination);
    } else {
        gs_.at(destination, advP(plane::kTower1)) = 0;
        gs_.at(destination, advP(plane::kTower2)) = 0;
        gs_.at(destination, advP(plane::kAmbar)) = 0;
        gs_.at(destination, advP(plane::kTown)) = 0;
        if (gs_.at(destination, plane::kPine) == 1) {
            removeValue(gs_.treeList(), destination);
            gs_.at(destination, plane::kPine) = 0;
        }
        if (gs_.at(destination, plane::kGraves) == 1) {
            removeValue(gs_.graveList(), destination);
            gs_.at(destination, plane::kGraves) = 0;
        }
    }
    gs_.setUnitType(destination, static_cast<uint8_t>(unitType));
    gs_.at(destination, advP(plane::kMoney)) = 0;

    const int length = static_cast<int>(actualRoots.size());
    const int newMoney = oldMoney / length;
    int remainder = oldMoney % length;
    std::vector<int> newMoneyList(length, newMoney);
    for (int i = 0; remainder > 0; --remainder, i = (i + 1) % length)
        ++newMoneyList[i];

    int keyForNewProvince =
        advProvinces.empty() ? 1 : advProvinces.rbegin()->first + 1;

    for (int ri = 0; ri < length; ++ri) {
        DetectedProvince& dp = newDetected[ri];
        if (dp.hexes.empty()) {
            // detection was cached only when >1 root; for single roots redo
            dp = detectProvince(actualRoots[ri], true, 0);
        }
        if (dp.hexes.size() > 1) {
            Province p;
            p.hexes = dp.hexes;
            p.ambarCost = 12 + dp.numBarns * 2;
            for (const Hex& h : dp.hexes)
                gs_.at(h, advP(plane::kProvinceIndex)) = keyForNewProvince;
            advProvinces[keyForNewProvince] = std::move(p);

            changeIncomeInProvince(keyForNewProvince, dp.income, true);
            changeMoneyInProvince(keyForNewProvince, newMoneyList[ri], true);

            if (!dp.hasTown) {
                const Hex place = findPlaceForNewTown(keyForNewProvince);
                gs_.at(place, advP(plane::kTown)) = 1;
            }
            ++keyForNewProvince;
        } else {
            // single detached hex — discard as a province
            const Hex h = dp.hexes.front();
            gs_.at(h, advP(plane::kProvinceIndex)) = 0;
            gs_.at(h, advP(plane::kMoney)) = 0;
            if (gs_.unitType(h) == 0) {
                gs_.at(h, advP(plane::kTown)) = 0;
                gs_.at(h, advP(plane::kTower1)) = 0;
                gs_.at(h, advP(plane::kTower2)) = 0;
                gs_.at(h, advP(plane::kAmbar)) = 0;
                gs_.at(h, advP(plane::kIncome)) = 0;
            } else {
                gs_.deadHexes().push_back(h);
            }
        }
    }
}

// ==========================================================================
// Public move application
// ==========================================================================
void GameRules::applyUnitMove(const Hex& from, int moveIndex) {
    const int n = gs_.config().numMoveTargets();
    auto target = gs_.geometry().hexByLayer(moveIndex, from, n);
    if (!target || *target == from) return;  // stay in place
    const Hex to = *target;

    const int unit = gs_.unitType(from);
    if (unit == 0) return;

    gs_.at(from, gs_.activePlane(plane::kUnit1 + unit - 1)) = 0;
    gs_.setUnitType(from, 0);

    const bool hasAlready = gs_.unitType(to) > 0;
    const bool enemyHasHim =
        hasAlready && gs_.at(to, gs_.activePlane(plane::kPlayerHexes)) == 0;

    removeValue(gs_.activeUnits(), from);

    performOneUnitMove(from, to, unit);

    if (!hasAlready) {
        gs_.activeUnits().push_back(to);
    } else if (enemyHasHim) {
        removeValue(gs_.adversaryUnits(), to);
        gs_.activeUnits().push_back(to);
    }
    // friendly merge: destination already in activeUnits
}

void GameRules::applySpend(const Hex& hexagon, const Hex& spendHex, int action) {
    if (action == kSpendNothing) return;
    auto activeP = [this](int rel) { return gs_.activePlane(rel); };

    if (action < 3 || action == 5) {
        const int unit = actionToUnit(action);
        const bool hasAlready = gs_.unitType(hexagon) > 0;
        const bool enemyHasHim =
            hasAlready &&
            gs_.at(hexagon, activeP(plane::kPlayerHexes)) == 0;

        const int province = gs_.at(spendHex, activeP(plane::kProvinceIndex));
        changeMoneyInProvince(
            province, gs_.at(spendHex, activeP(plane::kMoney)) - unitCost(unit),
            false);
        changeIncomeInProvince(
            province, gs_.at(spendHex, activeP(plane::kIncome)) + unitFood(unit),
            false);
        performOneUnitMove(spendHex, hexagon, unit);
        if (!hasAlready) {
            gs_.activeUnits().push_back(hexagon);
        } else if (enemyHasHim) {
            removeValue(gs_.adversaryUnits(), hexagon);
            gs_.activeUnits().push_back(hexagon);
        }
    } else if (action == 3) {
        const int province = gs_.at(spendHex, activeP(plane::kProvinceIndex));
        changeMoneyInProvince(province,
                              gs_.at(spendHex, activeP(plane::kMoney)) - 15, false);
        changeIncomeInProvince(province,
                               gs_.at(spendHex, activeP(plane::kIncome)) - 1, false);
        gs_.at(hexagon, activeP(plane::kTower1)) = 1;
    } else if (action == 4) {
        int gain = 0;
        if (gs_.at(hexagon, activeP(plane::kTower1)) != 0) {
            gain = 1;
            gs_.at(hexagon, activeP(plane::kTower1)) = 0;
        }
        const int province = gs_.at(spendHex, activeP(plane::kProvinceIndex));
        changeMoneyInProvince(province,
                              gs_.at(spendHex, activeP(plane::kMoney)) - 35, false);
        changeIncomeInProvince(
            province, gs_.at(spendHex, activeP(plane::kIncome)) - 6 + gain, false);
        gs_.at(hexagon, activeP(plane::kTower2)) = 1;
    } else if (action == 6) {
        const int province = gs_.at(spendHex, activeP(plane::kProvinceIndex));
        auto it = gs_.activeProvinces().find(province);
        if (it == gs_.activeProvinces().end()) return;
        changeMoneyInProvince(
            province,
            gs_.at(spendHex, activeP(plane::kMoney)) - it->second.ambarCost, false);
        changeIncomeInProvince(province,
                               gs_.at(spendHex, activeP(plane::kIncome)) + 4, false);
        it->second.ambarCost += 2;
        gs_.at(hexagon, activeP(plane::kAmbar)) = 1;
    }
}

void GameRules::endMove() {
    gs_.incrementStep();
    updateAfterMove();
    gs_.changeActivePlayer();
}

GameResult GameRules::checkGameEnd() const {
    bool onlyNoMoneyAndZeroIncome = true;
    if (!gs_.activeUnits().empty()) {
        onlyNoMoneyAndZeroIncome = false;
    } else {
        for (const auto& [idx, province] : gs_.activeProvinces()) {
            if (province.hexes.empty()) continue;
            const Hex sample = province.hexes.front();
            if (gs_.at(sample, gs_.activePlane(plane::kMoney)) != 0 ||
                gs_.at(sample, gs_.activePlane(plane::kIncome)) > 0) {
                onlyNoMoneyAndZeroIncome = false;
                break;
            }
        }
    }
    const int step = gs_.step();
    if (onlyNoMoneyAndZeroIncome || gs_.activeProvinces().empty()) {
        return GameResult::ActivePlayerLost;
    }
    if (gs_.adversaryProvinces().empty()) {
        // adversary is already dead — active player wins; encode as
        // "active player lost" from the adversary's perspective is handled
        // by the caller; we surface it as a special case.
        return GameResult::ActivePlayerLost;  // caller checks who has provinces
    }
    if (step - gs_.lastExpandedStep(0) >= 500 ||
        step - gs_.lastExpandedStep(1) >= 500 ||
        step >= gs_.config().maxMoves) {
        return GameResult::Draw;
    }
    return GameResult::Ongoing;
}

}  // namespace hexgame