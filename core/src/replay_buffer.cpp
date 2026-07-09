#include "replay_buffer.hpp"

namespace hexgame {

ReplayBuffer::ReplayBuffer(size_t capacity, uint64_t seed)
    : capacity_(capacity), rng_(seed) {
    buffer_.reserve(std::min<size_t>(capacity, 1 << 20));
}

void ReplayBuffer::add(std::vector<TrainingSample>&& samples) {
    std::lock_guard<std::mutex> lock(mu_);
    for (auto& s : samples) {
        if (buffer_.size() < capacity_) {
            buffer_.push_back(std::move(s));
        } else {
            buffer_[nextIdx_] = std::move(s);
            full_ = true;
        }
        nextIdx_ = (nextIdx_ + 1) % capacity_;
    }
}

size_t ReplayBuffer::size() const {
    std::lock_guard<std::mutex> lock(mu_);
    return buffer_.size();
}

std::vector<TrainingSample> ReplayBuffer::sample(size_t batchSize) {
    std::lock_guard<std::mutex> lock(mu_);
    std::vector<TrainingSample> out;
    if (buffer_.empty()) return out;
    out.reserve(batchSize);
    std::uniform_int_distribution<size_t> dist(0, buffer_.size() - 1);
    for (size_t i = 0; i < batchSize; ++i) out.push_back(buffer_[dist(rng_)]);
    return out;
}

}  // namespace hexgame