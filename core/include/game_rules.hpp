#pragma once
// ---------------------------------------------------------------------------
// Game rules engine. Faithful C++ port of:
//   engine/game_process.py
//   engine/move_performer/actions_before_and_after_players_move.py
//   engine/move_performer/unit_move.py
//   engine/move_performer/spend_money.py
//   engine/move_performer/probability_normalization.py
//   engine/move_performer/state_information.py
//   engine/move_performer/state_matrix_change_tools.py
// ---------------------------------------------------------------------------

#include <array>
#include <vector>

#include "game_state.hpp"

namespace hexgame {

// Cost / income tables (state_information.py)
inline int unitFood(int unitType) {
    static constexpr std::array<int, 5> t = {0, -2, -6, -18, -36};
    return t[unitType];
}
inline int unitCost(int unitType) {
    static constexpr std::array<int, 5> t = {0, 10, 20, 30, 40};
    return t[unitType];
}
// spend action index -> unit type  {0:1, 1:2, 2:3, 5:4}
inline int actionToUnit(int action) {
    switch (action) {
        case 0: return 1;
        case 1: return 2;
        case 2: return 3;
        case 5: return 4;
        default: return 0;
    }
}

inline constexpr int kNumSpendActions = 8;
inline constexpr int kSpendNothing = 7;

// Result of one full player move.
enum class GameResult { Ongoing, ActivePlayerLost, Draw };

class GameRules {
public:
    explicit GameRules(GameState& state) : gs_(state) {}

    // ---- Pre-move dynamics (actions_before_and_after_players_move.py) ----
    // Starvation, income accrual, graves -> trees.
    void updateBeforeMove();

    // Tree growth after a move (update_after_move).
    void updateAfterMove();

    // ---- Legality masks used by MCTS / policy heads ----

    // Which hexes contain movable friendly units.
    std::vector<Hex> hexesWithFriendlyUnits() const;

    // For a unit standing on `hexagon`, computes a 0/1 mask of legal move
    // targets (size = numMoveTargets). Port of
    // normalise_the_probabilities_of_actions (mask part only).
    // Always allows "stay" if nothing else is possible.
    std::vector<uint8_t> legalUnitMoves(const Hex& hexagon) const;

    // For spending on `hexagon`, computes the 0/1 mask of legal spend actions
    // and the province hex from which money is spent.
    // Port of normalise_the_probabilities_of_spending (mask part only).
    struct SpendLegality {
        std::array<uint8_t, kNumSpendActions> mask{};
        Hex spendHex;
    };
    SpendLegality legalSpends(const Hex& hexagon) const;

    // ---- Move application ----

    // Move a unit from `from` using target index `moveIndex` (in the
    // numMoveTargets layout). Assumes legality was checked.
    void applyUnitMove(const Hex& from, int moveIndex);

    // Spend on `hexagon` with `action` from `spendHex`. Assumes legality.
    void applySpend(const Hex& hexagon, const Hex& spendHex, int action);

    // End-of-move: switch player, increment step counter.
    void endMove();

    // Port of game_end_check(): loss/draw detection for the *active* player.
    GameResult checkGameEnd() const;

    // Defence strength of an enemy hex (state_information.py).
    int enemyHexDefence(const Hex& hexagon) const;

private:
    int enemyBuilding(const Hex& hexagon) const;

    // BFS_for_connectivity — reachable hexes within move range.
    std::vector<Hex> bfsConnectivity(const Hex& origin) const;

    // Province utility functions (state_matrix_change_tools.py)
    void changeMoneyInProvince(int provinceIndex, int newMoney, bool adversary);
    void changeIncomeInProvince(int provinceIndex, int newIncome, bool adversary);

    // unit_move.py helpers
    void performOneUnitMove(const Hex& departure, const Hex& destination,
                            int unitType);
    void mergeProvinces(const std::vector<int>& provincesToMerge,
                        const Hex& junctionHex);
    // detect_province_by_hex_with_income
    struct DetectedProvince {
        std::vector<Hex> hexes;
        int income = 0;
        bool hasTown = false;
        int numBarns = 0;
    };
    DetectedProvince detectProvince(const Hex& hexagon, bool adversary,
                                    int newProvinceIndex);
    Hex findPlaceForNewTown(int provinceIndex);

    GameState& gs_;
};

}  // namespace hexgame