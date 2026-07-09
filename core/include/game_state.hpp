#pragma once
// ---------------------------------------------------------------------------
// Game state. Faithful C++ port of engine/state_generation.py.
//
// The state is stored as a (H x W x 28) int32 tensor plus auxiliary
// bookkeeping structures (province maps, unit lists, tree/grave lists),
// exactly mirroring the Python GameState.
// ---------------------------------------------------------------------------

#include <cstdint>
#include <map>
#include <random>
#include <vector>

#include "hex_geometry.hpp"

namespace hexgame {

// Feature-plane indices -- identical to the Python dictionaries.
namespace plane {
// general
inline constexpr int kBlack = 0;
inline constexpr int kGray = 1;
inline constexpr int kGraves = 2;
inline constexpr int kPine = 3;
// active player (offset 4)
inline constexpr int kActiveBase = 4;
// adversary player (offset 16)
inline constexpr int kAdversaryBase = 16;
// per-player relative offsets
inline constexpr int kUnit1 = 0;
inline constexpr int kUnit2 = 1;
inline constexpr int kUnit3 = 2;
inline constexpr int kUnit4 = 3;
inline constexpr int kPlayerHexes = 4;
inline constexpr int kTower1 = 5;
inline constexpr int kTower2 = 6;
inline constexpr int kAmbar = 7;
inline constexpr int kTown = 8;
inline constexpr int kIncome = 9;
inline constexpr int kMoney = 10;
inline constexpr int kProvinceIndex = 11;

inline constexpr int kNumPlanes = 28;
inline constexpr int kPerPlayerPlanes = 12;
}  // namespace plane

struct GameConfig {
    int width = 10;
    int height = 10;
    int moveSize = 2;               // 2 -> 19 targets, 4 -> 61 targets
    int maxMoves = 400;
    int islands = 2;
    int islandSize = 7;
    double treeProbability = 0.1;
    double treeGrowthProbability = 0.01;

    int numMoveTargets() const {
        return moveSize == 4 ? kMoveTargets4 : kMoveTargets2;
    }
    int stayIndex() const { return moveSize == 4 ? kStayIndex61 : kStayIndex19; }
};

struct Province {
    std::vector<Hex> hexes;
    int ambarCost = 12;
};

class GameState {
public:
    GameState(const GameConfig& cfg, uint64_t seed);

    // ---- Random map generation (port of generate_random_game) ----
    void generateRandomGame();

    // ---- raw state access ----
    int32_t& at(const Hex& h, int p) {
        return state_[(h.row * cfg_.width + h.col) * plane::kNumPlanes + p];
    }
    int32_t at(const Hex& h, int p) const {
        return state_[(h.row * cfg_.width + h.col) * plane::kNumPlanes + p];
    }
    // active-player plane
    int activePlane(int rel) const { return plane::kActiveBase + rel; }
    // adversary plane
    int adversaryPlane(int rel) const { return plane::kAdversaryBase + rel; }

    uint8_t unitType(const Hex& h) const {
        return unitType_[h.row * cfg_.width + h.col];
    }
    void setUnitType(const Hex& h, uint8_t t) {
        unitType_[h.row * cfg_.width + h.col] = t;
    }

    const GameConfig& config() const { return cfg_; }
    const HexGeometry& geometry() const { return geo_; }
    std::mt19937_64& rng() { return rng_; }

    // ---- province / unit bookkeeping (mirrors the Python attributes) ----
    std::map<int, Province>& activeProvinces() {
        return activePlayer_ == 0 ? p1Provinces_ : p2Provinces_;
    }
    std::map<int, Province>& adversaryProvinces() {
        return activePlayer_ == 0 ? p2Provinces_ : p1Provinces_;
    }
    const std::map<int, Province>& activeProvinces() const {
        return activePlayer_ == 0 ? p1Provinces_ : p2Provinces_;
    }
    const std::map<int, Province>& adversaryProvinces() const {
        return activePlayer_ == 0 ? p2Provinces_ : p1Provinces_;
    }
    std::vector<Hex>& activeUnits() {
        return activePlayer_ == 0 ? p1Units_ : p2Units_;
    }
    std::vector<Hex>& adversaryUnits() {
        return activePlayer_ == 0 ? p2Units_ : p1Units_;
    }
    const std::vector<Hex>& activeUnits() const {
        return activePlayer_ == 0 ? p1Units_ : p2Units_;
    }
    const std::vector<Hex>& adversaryUnits() const {
        return activePlayer_ == 0 ? p2Units_ : p1Units_;
    }

    std::vector<Hex>& treeList() { return treeList_; }
    std::vector<Hex>& graveList() { return graveList_; }
    std::vector<Hex>& deadHexes() { return deadHexes_; }
    const std::vector<Hex>& activeHexes() const { return activeHexes_; }

    int activePlayer() const { return activePlayer_; }
    int step() const { return step_; }
    void incrementStep() { ++step_; }

    int lastExpandedStep(int player) const {
        return player == 0 ? p1LastExpandedStep_ : p2LastExpandedStep_;
    }
    void setLastExpandedStep(int player, int step) {
        (player == 0 ? p1LastExpandedStep_ : p2LastExpandedStep_) = step;
    }

    // Swap active/adversary players and transpose the state planes,
    // exactly as change_active_player() in the Python engine.
    void changeActivePlayer();

    // Adjacent friendly hexes of the given player (0 = active, 1 = adversary).
    std::vector<Hex> adjacentFriendlyHexes(const Hex& h, bool adversary) const;

    // Neural network input: (kNumPlanes, H, W) float tensor with
    // money/income/province normalized. Written into `out` which must
    // hold kNumPlanes * H * W floats.
    void encodeForNetwork(float* out) const;

    // Whole raw state (row-major H x W x 28).
    const std::vector<int32_t>& raw() const { return state_; }

    // Deep copy (states are value types; this is used by MCTS).
    GameState clone() const { return *this; }

private:
    void spawnIsland(const Hex& start, int size);
    void uniteIslandsWithRoads(const std::vector<Hex>& centers);
    void addTrees();
    Hex findGoodPlaceForNewProvince(int fraction);
    void spawnProvince(const Hex& spawnHex, int startingPotential, int fraction);
    void spawnProvinces();
    Hex randomHexInsideBounds();

    GameConfig cfg_;
    HexGeometry geo_;
    std::mt19937_64 rng_;

    std::vector<int32_t> state_;    // H*W*28
    std::vector<uint8_t> unitType_; // H*W

    std::vector<Hex> activeHexes_;
    std::vector<Hex> treeList_;
    std::vector<Hex> graveList_;
    std::vector<Hex> deadHexes_;

    int activePlayer_ = 0;
    int step_ = 0;

    std::map<int, Province> p1Provinces_;
    std::map<int, Province> p2Provinces_;
    std::vector<Hex> p1Units_;
    std::vector<Hex> p2Units_;

    int p1LastExpandedStep_ = 0;
    int p2LastExpandedStep_ = 0;
};

}  // namespace hexgame