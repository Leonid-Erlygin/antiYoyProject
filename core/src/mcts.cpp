#include "mcts.hpp"

#include <algorithm>
#include <cmath>

namespace hexgame {

Mcts::Mcts(const GameConfig& gameCfg, const MctsConfig& mctsCfg,
           const ActionSpace& actions, InferenceServer* server, uint64_t seed)
    : gameCfg_(gameCfg),
      cfg_(mctsCfg),
      actions_(actions),
      server_(server),
      rng_(seed) {}

float Mcts::expand(MctsNode* node, GameState& state,
                   const std::vector<uint8_t>& unitMoved, GameRules& rules) {
    node->playerToMove = state.activePlayer();

    const auto legal = actions_.legalMask(state, rules, unitMoved);

    // network evaluation
    std::vector<float> encoded(
        static_cast<size_t>(plane::kNumPlanes) * gameCfg_.height * gameCfg_.width);
    state.encodeForNetwork(encoded.data());
    InferenceResult res = server_->infer(encoded);

    // priors on legal actions
    float legalSum = 0.f;
    for (int a = 0; a < actions_.size(); ++a) {
        if (legal[a]) legalSum += res.policy[a];
    }
    const float eps = 1e-8f;
    for (int a = 0; a < actions_.size(); ++a) {
        if (!legal[a]) continue;
        MctsNode::Edge edge;
        edge.prior = legalSum > eps ? res.policy[a] / legalSum
                                    : 1.0f / std::max<size_t>(1, node->edges.size() + 1);
        node->edges.emplace(a, std::move(edge));
    }
    node->expanded = true;
    return res.value;
}

std::vector<float> Mcts::search(const GameState& rootState,
                                const std::vector<uint8_t>& rootUnitMoved,
                                bool addNoise) {
    MctsNode root;
    {
        GameState s = rootState.clone();
        GameRules rules(s);
        expand(&root, s, rootUnitMoved, rules);
    }

    if (addNoise && !root.edges.empty()) {
        std::gamma_distribution<double> gamma(cfg_.dirichletAlpha, 1.0);
        std::vector<double> noise;
        noise.reserve(root.edges.size());
        double sum = 0;
        for (size_t i = 0; i < root.edges.size(); ++i) {
            noise.push_back(gamma(rng_));
            sum += noise.back();
        }
        size_t i = 0;
        for (auto& [a, edge] : root.edges) {
            edge.prior = static_cast<float>(
                (1 - cfg_.dirichletEpsilon) * edge.prior +
                cfg_.dirichletEpsilon * noise[i++] / std::max(sum, 1e-12));
        }
    }

    for (int sim = 0; sim < cfg_.simulations; ++sim) {
        GameState state = rootState.clone();
        GameRules rules(state);
        std::vector<uint8_t> unitMoved = rootUnitMoved;

        MctsNode* node = &root;
        std::vector<SimStep> path;
        float leafValue = 0.f;
        int leafPlayer = state.activePlayer();
        bool terminal = false;

        while (node->expanded && !terminal) {
            // PUCT selection
            const double sqrtTotal =
                std::sqrt(static_cast<double>(std::max(1, node->totalVisits)));
            int bestAction = -1;
            double bestScore = -1e30;
            for (auto& [a, edge] : node->edges) {
                const double q =
                    edge.visits > 0 ? edge.valueSum / edge.visits : 0.0;
                const double u =
                    cfg_.cPuct * edge.prior * sqrtTotal / (1.0 + edge.visits);
                const double score = q + u;
                if (score > bestScore) {
                    bestScore = score;
                    bestAction = a;
                }
            }
            if (bestAction < 0) break;

            path.push_back({node, bestAction});

            const Action act = actions_.decode(bestAction);
            const int playerBefore = state.activePlayer();
            const bool turnEnded = actions_.apply(state, rules, act, unitMoved);

            if (turnEnded) {
                // new turn for the (now) active player: pre-move update
                std::fill(unitMoved.begin(), unitMoved.end(), 0);
                rules.updateBeforeMove();
                const GameResult end = rules.checkGameEnd();
                if (end == GameResult::ActivePlayerLost) {
                    // the player who just moved (playerBefore) wins
                    leafValue = state.activePlayer() == playerBefore ? -1.f : 1.f;
                    leafPlayer = playerBefore;
                    leafValue = 1.f;  // from playerBefore's perspective
                    terminal = true;
                    break;
                }
                if (end == GameResult::Draw) {
                    leafPlayer = state.activePlayer();
                    leafValue = 0.f;
                    terminal = true;
                    break;
                }
            }

            auto& edge = node->edges[bestAction];
            if (!edge.child) edge.child = std::make_unique<MctsNode>();
            node = edge.child.get();
        }

        if (!terminal) {
            leafPlayer = state.activePlayer();
            leafValue = expand(node, state, unitMoved, rules);
        }

        // backup: value is from leafPlayer's perspective
        for (auto it = path.rbegin(); it != path.rend(); ++it) {
            auto& edge = it->node->edges[it->action];
            const float v =
                it->node->playerToMove == leafPlayer ? leafValue : -leafValue;
            edge.valueSum += v;
            edge.visits += 1;
            it->node->totalVisits += 1;
        }
    }

    // visit distribution
    std::vector<float> dist(actions_.size(), 0.f);
    float total = 0.f;
    for (const auto& [a, edge] : root.edges) {
        dist[a] = static_cast<float>(edge.visits);
        total += edge.visits;
    }
    if (total > 0) {
        for (auto& d : dist) d /= total;
    } else {
        // fallback to priors
        for (const auto& [a, edge] : root.edges) dist[a] = edge.prior;
    }
    return dist;
}

int Mcts::selectAction(const std::vector<float>& visitDist, double temperature) {
    if (temperature <= 1e-6) {
        return static_cast<int>(std::distance(
            visitDist.begin(), std::max_element(visitDist.begin(), visitDist.end())));
    }
    std::vector<double> probs(visitDist.size());
    double sum = 0;
    for (size_t i = 0; i < visitDist.size(); ++i) {
        probs[i] = std::pow(static_cast<double>(visitDist[i]), 1.0 / temperature);
        sum += probs[i];
    }
    std::uniform_real_distribution<double> uni(0.0, sum);
    double r = uni(rng_);
    for (size_t i = 0; i < probs.size(); ++i) {
        r -= probs[i];
        if (r <= 0) return static_cast<int>(i);
    }
    return static_cast<int>(probs.size() - 1);
}

}  // namespace hexgame