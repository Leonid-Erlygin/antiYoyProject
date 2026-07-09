#include "game_state.hpp"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstring>

namespace hexgame {

GameState::GameState(const GameConfig& cfg, uint64_t seed)
    : cfg_(cfg),
      geo_(cfg.height, cfg.width),
      rng_(seed),
      state_(static_cast<size_t>(cfg.height) * cfg.width * plane::kNumPlanes, 0),
      unitType_(static_cast<size_t>(cfg.height) * cfg.width, 0) {
    // everything starts black
    for (int r = 0; r < cfg_.height; ++r)
        for (int c = 0; c < cfg_.width; ++c) at(Hex(r, c), plane::kBlack) = 1;
}

void GameState::changeActivePlayer() {
    activePlayer_ = 1 - activePlayer_;
    // transpose active / adversary planes
    const int n = cfg_.height * cfg_.width;
    for (int i = 0; i < n; ++i) {
        int32_t* cell = &state_[static_cast<size_t>(i) * plane::kNumPlanes];
        for (int rel = 0; rel < plane::kPerPlayerPlanes; ++rel) {
            std::swap(cell[plane::kActiveBase + rel],
                      cell[plane::kAdversaryBase + rel]);
        }
    }
}

std::vector<Hex> GameState::adjacentFriendlyHexes(const Hex& h, bool adversary) const {
    std::vector<Hex> out;
    out.reserve(6);
    const int p = adversary ? adversaryPlane(plane::kPlayerHexes)
                            : activePlane(plane::kPlayerHexes);
    for (int d = 0; d < 6; ++d) {
        if (auto a = geo_.adjacent(h, d)) {
            if (at(*a, p) == 1) out.push_back(*a);
        }
    }
    return out;
}

// --------------------------------------------------------------------------
// Map generation (ports of spawnIsland / uniteIslandsWithRoads / addTrees /
// findGoodPlaceForNewProvince / spawnProvince / spawnProvinces)
// --------------------------------------------------------------------------

Hex GameState::randomHexInsideBounds() {
    std::uniform_int_distribution<int> dr(0, cfg_.height - 1);
    std::uniform_int_distribution<int> dc(0, cfg_.width - 1);
    return Hex(dr(rng_), dc(rng_));
}

void GameState::spawnIsland(const Hex& start, int size) {
    std::vector<uint8_t> gen(cfg_.height * cfg_.width, 0);
    std::vector<uint8_t> genPotential(cfg_.height * cfg_.width, 0);
    genPotential[geo_.index(start)] = static_cast<uint8_t>(size);
    std::vector<Hex> propagation = {start};
    std::uniform_int_distribution<int> dist(0, size - 1);

    while (!propagation.empty()) {
        Hex h = propagation.back();
        propagation.pop_back();
        gen[geo_.index(start)] = 1;

        if (dist(rng_) > genPotential[geo_.index(h)]) continue;
        const bool wasNotGray = at(h, plane::kGray) != 1;
        if (wasNotGray) activeHexes_.push_back(h);
        at(h, plane::kGray) = 1;
        at(h, plane::kBlack) = 0;

        if (genPotential[geo_.index(h)] == 0 || !wasNotGray) continue;

        for (int d = 0; d < 6; ++d) {
            if (auto adj = geo_.adjacent(h, d)) {
                if (!gen[geo_.index(*adj)] &&
                    std::count(propagation.begin(), propagation.end(), *adj) == 0) {
                    genPotential[geo_.index(*adj)] =
                        static_cast<uint8_t>(genPotential[geo_.index(h)] - 1);
                    propagation.push_back(*adj);
                }
            }
        }
    }
}

void GameState::uniteIslandsWithRoads(const std::vector<Hex>& centers) {
    const double r = 20.0;  // road step scale, identical to the Python default
    auto [sx, sy] = geo_.pixelCoordinates(centers[0], r);
    auto [ex, ey] = geo_.pixelCoordinates(centers[1], r);
    const double distance = std::hypot(sx - ex, sy - ey);
    const double angle = std::arg(std::complex<double>(ex - sx, ey - sy));
    const double delta = r / 2.0;
    const int n = static_cast<int>(distance / delta);
    Hex prev(-1, -1);
    for (int i = 0; i < n; ++i) {
        const double cx = sx + delta * i * std::cos(angle);
        const double cy = sy + delta * i * std::sin(angle);
        Hex h = geo_.hexByPixel(cx, cy, r);
        if (h != prev) {
            spawnIsland(h, 2);
            prev = h;
        }
    }
}

void GameState::addTrees() {
    std::uniform_real_distribution<double> uni(0.0, 1.0);
    for (const Hex& h : activeHexes_) {
        if (uni(rng_) < cfg_.treeProbability &&
            at(h, activePlane(plane::kTown)) == 0 &&
            at(h, adversaryPlane(plane::kTown)) == 0) {
            treeList_.push_back(h);
            at(h, plane::kPine) = 1;
        }
    }
}

Hex GameState::findGoodPlaceForNewProvince(int fraction) {
    if (fraction == 0) {
        std::uniform_int_distribution<size_t> d(0, activeHexes_.size() - 1);
        return activeHexes_[d(rng_)];
    }
    // BFS-like wavefront starting from gray cells to find the most distant.
    std::vector<int> zone(cfg_.height * cfg_.width, INT32_MIN);
    for (const Hex& h : activeHexes_)
        if (at(h, plane::kGray) == 1) zone[geo_.index(h)] = -1;

    int step = 0;
    while (true) {
        bool expanded = false;
        for (const Hex& h : activeHexes_) {
            if (zone[geo_.index(h)] != step) continue;
            for (int d = 0; d < 6; ++d) {
                if (auto adj = geo_.adjacent(h, d)) {
                    if (at(*adj, plane::kBlack) == 1) continue;
                    if (zone[geo_.index(*adj)] != -1) continue;
                    zone[geo_.index(*adj)] = step + 1;
                    expanded = true;
                }
            }
        }
        if (!expanded) break;
        ++step;
    }
    Hex result(-1, -1);
    for (const Hex& h : activeHexes_) {
        if (!result.valid() || zone[geo_.index(h)] > zone[geo_.index(result)])
            result = h;
    }
    return result;
}

void GameState::spawnProvince(const Hex& spawnHex, int startingPotential,
                              int fraction) {
    const bool isPlayer1 = fraction == 0;
    auto& provinces = isPlayer1 ? p1Provinces_ : p2Provinces_;
    provinces[1] = Province{};

    const int hexPlane =
        isPlayer1 ? activePlane(plane::kPlayerHexes) : adversaryPlane(plane::kPlayerHexes);
    const int provPlane = isPlayer1 ? activePlane(plane::kProvinceIndex)
                                    : adversaryPlane(plane::kProvinceIndex);
    const int incomePlane =
        isPlayer1 ? activePlane(plane::kIncome) : adversaryPlane(plane::kIncome);
    const int moneyPlane =
        isPlayer1 ? activePlane(plane::kMoney) : adversaryPlane(plane::kMoney);

    std::vector<uint8_t> genPotential(cfg_.height * cfg_.width, 0);
    std::vector<Hex> propagation = {spawnHex};
    genPotential[geo_.index(spawnHex)] = static_cast<uint8_t>(startingPotential);
    std::uniform_int_distribution<int> dist(0, startingPotential - 1);

    while (!propagation.empty()) {
        Hex h = propagation.back();
        propagation.pop_back();
        if (dist(rng_) > genPotential[geo_.index(h)]) continue;
        at(h, hexPlane) = 1;
        provinces[1].hexes.push_back(h);
        at(h, provPlane) = 1;
        at(h, plane::kGray) = 0;
        if (genPotential[geo_.index(h)] == 0) continue;
        for (int d = 0; d < 6; ++d) {
            if (auto adj = geo_.adjacent(h, d)) {
                if (std::count(propagation.begin(), propagation.end(), *adj) == 0 &&
                    at(*adj, plane::kBlack) == 0 && at(*adj, plane::kGray) == 1) {
                    genPotential[geo_.index(*adj)] =
                        static_cast<uint8_t>(genPotential[geo_.index(h)] - 1);
                    propagation.push_back(*adj);
                }
            }
        }
    }

    int trees = 0;
    for (const Hex& h : provinces[1].hexes)
        if (at(h, plane::kPine) == 1) ++trees;
    const int income = static_cast<int>(provinces[1].hexes.size()) - trees;
    for (const Hex& h : provinces[1].hexes) {
        at(h, incomePlane) = income;
        at(h, moneyPlane) = 10;
    }
}

void GameState::spawnProvinces() {
    for (int fraction = 0; fraction < 2; ++fraction) {
        Hex h = findGoodPlaceForNewProvince(fraction);
        at(h, plane::kPine) = 0;
        treeList_.erase(std::remove(treeList_.begin(), treeList_.end(), h),
                        treeList_.end());
        const int hexPlane = fraction == 0 ? activePlane(plane::kPlayerHexes)
                                           : adversaryPlane(plane::kPlayerHexes);
        const int townPlane =
            fraction == 0 ? activePlane(plane::kTown) : adversaryPlane(plane::kTown);
        at(h, hexPlane) = 1;
        at(h, townPlane) = 1;
        at(h, plane::kGray) = 0;
        spawnProvince(h, fraction + 1, fraction);
    }
}

void GameState::generateRandomGame() {
    std::vector<Hex> centers;
    for (int i = 0; i < cfg_.islands; ++i) {
        Hex h = randomHexInsideBounds();
        centers.push_back(h);
        spawnIsland(h, cfg_.islandSize);
    }
    if (centers.size() >= 2) uniteIslandsWithRoads(centers);
    addTrees();
    spawnProvinces();
}

// --------------------------------------------------------------------------
// Neural network encoding
// --------------------------------------------------------------------------
void GameState::encodeForNetwork(float* out) const {
    const int hw = cfg_.height * cfg_.width;
    // Layout: (plane, row, col). Money / income get log-scaled; province
    // indices are binarized (province vs no-province).
    for (int p = 0; p < plane::kNumPlanes; ++p) {
        for (int i = 0; i < hw; ++i) {
            const int32_t v = state_[static_cast<size_t>(i) * plane::kNumPlanes + p];
            float f;
            if (p == plane::kActiveBase + plane::kMoney ||
                p == plane::kAdversaryBase + plane::kMoney) {
                f = std::log1p(std::max(0.0f, static_cast<float>(v))) / 6.0f;
            } else if (p == plane::kActiveBase + plane::kIncome ||
                       p == plane::kAdversaryBase + plane::kIncome) {
                f = static_cast<float>(v) / 20.0f;
            } else if (p == plane::kActiveBase + plane::kProvinceIndex ||
                       p == plane::kAdversaryBase + plane::kProvinceIndex) {
                f = v > 0 ? 1.0f : 0.0f;
            } else {
                f = static_cast<float>(v);
            }
            out[static_cast<size_t>(p) * hw + i] = f;
        }
    }
}

}  // namespace hexgame