#pragma once
// ---------------------------------------------------------------------------
// Parallel self-play: N worker threads generate games with MCTS, feeding a
// shared batched inference server; finished games are pushed to the replay
// buffer with the final outcome as the value target.
// ---------------------------------------------------------------------------

#include <functional>
#include <vector>

#include "action_space.hpp"
#include "config.hpp"
#include "mcts.hpp"
#include "neural_net.hpp"
#include "replay_buffer.hpp"

namespace hexgame {

// Plain aggregate so it can be returned by value; thread-safe accumulation
// happens inside SelfPlayEngine::run() with local atomics.
struct SelfPlayStats {
    int gamesFinished = 0;
    int firstPlayerWins = 0;
    int draws = 0;
    long long totalMoves = 0;
};

class SelfPlayEngine {
public:
    SelfPlayEngine(const TrainingConfig& cfg, const ActionSpace& actions,
                   InferenceServer* server, ReplayBuffer* buffer);

    // Plays cfg.selfPlay.gamesPerIteration games using
    // cfg.selfPlay.parallelWorkers threads. Blocking.
    SelfPlayStats run(uint64_t seedBase);

    // Plays a single game and returns +1 / -1 / 0 (first player's outcome).
    // Optional callback fires after every applied micro-action.
    int playOneGame(uint64_t seed, bool collectSamples,
                    std::vector<TrainingSample>* out,
                    const std::function<void(const GameState&, int move)>&
                        onMove = nullptr);

private:
    TrainingConfig cfg_;
    const ActionSpace& actions_;
    InferenceServer* server_;
    ReplayBuffer* buffer_;
};

}  // namespace hexgame