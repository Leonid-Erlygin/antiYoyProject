#include "action_space.hpp"

namespace hexgame {

namespace {
constexpr int kNumSpendChoices = 7;  // 8 minus explicit "do nothing"
}

ActionSpace::ActionSpace(const GameConfig& cfg)
    : cfg_(cfg),
      numTargets_(cfg.numMoveTargets()),
      cells_(cfg.height * cfg.width),
      spendBase_(cells_ * cfg.numMoveTargets()),
      total_(cells_ * cfg.numMoveTargets() + cells_ * kNumSpendChoices + 1) {}

int ActionSpace::encode(const Action& a) const {
    const int cellIdx = a.cell.row * cfg_.width + a.cell.col;
    switch (a.type) {
        case Action::Type::UnitMove:
            return cellIdx * numTargets_ + a.arg;
        case Action::Type::Spend:
            return spendBase_ + cellIdx * kNumSpendChoices + a.arg;
        case Action::Type::EndTurn:
            return endTurnIndex();
    }
    return endTurnIndex();
}

Action ActionSpace::decode(int flat) const {
    Action a;
    if (flat == endTurnIndex()) {
        a.type = Action::Type::EndTurn;
        return a;
    }
    if (flat < spendBase_) {
        a.type = Action::Type::UnitMove;
        const int cellIdx = flat / numTargets_;
        a.arg = flat % numTargets_;
        a.cell = Hex(cellIdx / cfg_.width, cellIdx % cfg_.width);
        return a;
    }
    const int rel = flat - spendBase_;
    a.type = Action::Type::Spend;
    const int cellIdx = rel / kNumSpendChoices;
    a.arg = rel % kNumSpendChoices;
    a.cell = Hex(cellIdx / cfg_.width, cellIdx % cfg_.width);
    return a;
}

std::vector<uint8_t> ActionSpace::legalMask(
    const GameState& gs, const GameRules& rules,
    const std::vector<uint8_t>& unitMovedThisTurn) const {
    std::vector<uint8_t> mask(total_, 0);
    mask[endTurnIndex()] = 1;  // ending the turn is always legal

    // unit moves
    for (const Hex& h : rules.hexesWithFriendlyUnits()) {
        const int cellIdx = h.row * cfg_.width + h.col;
        if (unitMovedThisTurn[cellIdx]) continue;
        const auto unitMask = rules.legalUnitMoves(h);
        const int stay = cfg_.stayIndex();
        for (int i = 0; i < numTargets_; ++i) {
            if (i == stay) continue;  // "stay" is expressed by not moving
            if (unitMask[i]) mask[cellIdx * numTargets_ + i] = 1;
        }
    }

    // spends
    for (int cellIdx = 0; cellIdx < cells_; ++cellIdx) {
        const Hex h(cellIdx / cfg_.width, cellIdx % cfg_.width);
        if (gs.at(h, plane::kBlack) == 1) continue;
        const auto spend = rules.legalSpends(h);
        for (int a = 0; a < kNumSpendChoices; ++a) {
            if (spend.mask[a]) mask[spendBase_ + cellIdx * kNumSpendChoices + a] = 1;
        }
    }
    return mask;
}

bool ActionSpace::apply(GameState& gs, GameRules& rules, const Action& a,
                        std::vector<uint8_t>& unitMovedThisTurn) const {
    switch (a.type) {
        case Action::Type::UnitMove: {
            const int n = cfg_.numMoveTargets();
            auto target = gs.geometry().hexByLayer(a.arg, a.cell, n);
            rules.applyUnitMove(a.cell, a.arg);
            if (target) {
                unitMovedThisTurn[target->row * cfg_.width + target->col] = 1;
            }
            unitMovedThisTurn[a.cell.row * cfg_.width + a.cell.col] = 0;
            return false;
        }
        case Action::Type::Spend: {
            const auto spend = rules.legalSpends(a.cell);
            rules.applySpend(a.cell, spend.spendHex, a.arg);
            // a newly bought/upgraded unit cannot move this turn
            if (a.arg < 3 || a.arg == 5) {
                unitMovedThisTurn[a.cell.row * cfg_.width + a.cell.col] = 1;
            }
            return false;
        }
        case Action::Type::EndTurn: {
            rules.endMove();
            return true;
        }
    }
    return true;
}

}  // namespace hexgame