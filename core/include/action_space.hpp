#pragma once
// ---------------------------------------------------------------------------
// Flat, MCTS-friendly action space.
//
// A player's turn consists of a sequence of micro-actions applied one by one:
//   - UNIT_MOVE(cell, target)   : move a unit at `cell` to move-target index
//   - SPEND(cell, spend_action) : spend money on `cell` (buy unit/building)
//   - END_TURN                  : finish the turn
//
// The MCTS tree branches on micro-actions, which keeps the branching factor
// tractable while preserving the full combinatorial richness of a turn.
//
// Flat encoding:
//   [0, H*W*T)                : unit moves     (cell * T + target)
//   [H*W*T, H*W*T + H*W*7)    : spends         (base + cell * 7 + action)
//   [last]                    : END_TURN
// where T = numMoveTargets (19 or 61). The 8th "do nothing" spend action is
// folded into END_TURN semantics and therefore excluded from the flat space.
// ---------------------------------------------------------------------------

#include <cstdint>
#include <vector>

#include "game_rules.hpp"
#include "game_state.hpp"

namespace hexgame {

struct Action {
    enum class Type : uint8_t { UnitMove, Spend, EndTurn };
    Type type = Type::EndTurn;
    Hex cell;
    int arg = 0;  // move-target index or spend-action index
};

class ActionSpace {
public:
    ActionSpace(const GameConfig& cfg);

    int size() const { return total_; }
    int unitMoveBase() const { return 0; }
    int spendBase() const { return spendBase_; }
    int endTurnIndex() const { return total_ - 1; }

    int encode(const Action& a) const;
    Action decode(int flat) const;

    // Legal-action mask for the current active player.
    // `movesUsed` marks cells whose units have already moved this turn
    // (a unit may only move once per turn).
    std::vector<uint8_t> legalMask(const GameState& gs, const GameRules& rules,
                                   const std::vector<uint8_t>& unitMovedThisTurn) const;

    // Apply a micro-action. Returns true if the turn ended.
    bool apply(GameState& gs, GameRules& rules, const Action& a,
               std::vector<uint8_t>& unitMovedThisTurn) const;

private:
    GameConfig cfg_;
    int numTargets_;
    int cells_;
    int spendBase_;
    int total_;
};

}  // namespace hexgame