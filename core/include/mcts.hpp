#pragma once
// ---------------------------------------------------------------------------
// PUCT Monte-Carlo Tree Search over the micro-action space.
// Each simulation clones the root state and replays actions along the path
// (states are small, cloning is cheap and keeps the tree memory-light).
// ---------------------------------------------------------------------------

#include <memory>
#include <random>
#include <unordered_map>
#include <vector>

#include "action_space.hpp"
#include "config.hpp"
#include "game_rules.hpp"
#include "game_state.hpp"
#include "neural_net.hpp"

namespace hexgame {

struct MctsNode {
    // sparse children: legal action -> child
    struct Edge {
        float prior = 0.f;
        int visits = 0;
        double valueSum = 0.0;
        std::unique_ptr<MctsNode> child;
    };
    std::unordered_map<int, Edge> edges;
    int totalVisits = 0;
    bool expanded = false;
    int playerToMove = 0;
};

class Mcts {
public:
    Mcts(const GameConfig& gameCfg, const MctsConfig& mctsCfg,
         const ActionSpace& actions, InferenceServer* server,
         uint64_t seed);

    // Runs simulations from (state, unitMovedThisTurn) and returns the visit
    // distribution over the flat action space (normalized), restricted to
    // legal actions.
    std::vector<float> search(const GameState& rootState,
                              const std::vector<uint8_t>& rootUnitMoved,
                              bool addNoise);

    // Sample or argmax an action from the visit distribution.
    int selectAction(const std::vector<float>& visitDist, double temperature);

private:
    struct SimStep {
        MctsNode* node;
        int action;
    };

    // Expand a leaf: query the network, set priors on legal actions.
    // Returns the value estimate from the active player's perspective.
    float expand(MctsNode* node, GameState& state,
                 const std::vector<uint8_t>& unitMoved, GameRules& rules);

    GameConfig gameCfg_;
    MctsConfig cfg_;
    const ActionSpace& actions_;
    InferenceServer* server_;
    std::mt19937_64 rng_;
};

}  // namespace hexgame