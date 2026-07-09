#pragma once
// ---------------------------------------------------------------------------
// Thread-safe replay buffer of (state, policy, value) training samples.
// ---------------------------------------------------------------------------

#include <mutex>
#include <random>
#include <vector>

namespace hexgame {

struct TrainingSample {
    std::vector<float> state;    // encoded network input
    std::vector<float> policy;   // MCTS visit distribution
    float value = 0.f;           // game outcome from the acting player's view
};

class ReplayBuffer {
public:
    ReplayBuffer(size_t capacity, uint64_t seed);

    void add(std::vector<TrainingSample>&& samples);
    size_t size() const;

    // Sample `batchSize` items uniformly with replacement.
    std::vector<TrainingSample> sample(size_t batchSize);

private:
    mutable std::mutex mu_;
    std::vector<TrainingSample> buffer_;
    size_t capacity_;
    size_t nextIdx_ = 0;
    bool full_ = false;
    std::mt19937_64 rng_;
};

}  // namespace hexgame