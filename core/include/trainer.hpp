#pragma once
// ---------------------------------------------------------------------------
// The full AlphaZero training loop:
//   repeat:
//     1. parallel self-play with the current best network
//     2. gradient updates from the replay buffer
//     3. periodic evaluation of candidate vs best; promotion on win-rate
//     4. checkpointing
// ---------------------------------------------------------------------------

#include <string>

#include "action_space.hpp"
#include "config.hpp"
#include "neural_net.hpp"
#include "replay_buffer.hpp"
#include "self_play.hpp"

namespace hexgame {

class Trainer {
public:
    explicit Trainer(const TrainingConfig& cfg);

    void run();

    // Load / save checkpoints.
    void saveCheckpoint(const std::string& path);
    void loadCheckpoint(const std::string& path);

private:
    double evaluateCandidate(uint64_t seedBase);
    void trainEpoch(int iteration);

    TrainingConfig cfg_;
    torch::Device device_;
    ActionSpace actions_;

    AlphaZeroNet bestNet_{nullptr};
    AlphaZeroNet candidateNet_{nullptr};
    std::unique_ptr<torch::optim::Adam> optimizer_;
    std::unique_ptr<InferenceServer> server_;
    std::unique_ptr<ReplayBuffer> buffer_;

    long long trainSteps_ = 0;
};

}  // namespace hexgame