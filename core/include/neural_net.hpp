#pragma once
// ---------------------------------------------------------------------------
// AlphaZero-style residual network with policy and value heads,
// plus a thread-safe batched inference server for parallel self-play.
// ---------------------------------------------------------------------------

#include <torch/torch.h>

#include <atomic>
#include <condition_variable>
#include <future>
#include <memory>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

#include "config.hpp"
#include "game_state.hpp"

namespace hexgame {

struct ResidualBlockImpl : torch::nn::Module {
    ResidualBlockImpl(int channels);
    torch::Tensor forward(torch::Tensor x);
    torch::nn::Conv2d conv1{nullptr}, conv2{nullptr};
    torch::nn::BatchNorm2d bn1{nullptr}, bn2{nullptr};
};
TORCH_MODULE(ResidualBlock);

struct AlphaZeroNetImpl : torch::nn::Module {
    AlphaZeroNetImpl(const GameConfig& game, const NetworkConfig& net,
                     int actionSize);

    // returns {policy_logits [B, A], value [B, 1]}
    std::pair<torch::Tensor, torch::Tensor> forward(torch::Tensor x);

    torch::nn::Conv2d stem{nullptr};
    torch::nn::BatchNorm2d stemBn{nullptr};
    torch::nn::ModuleList blocks;
    torch::nn::Conv2d policyConv{nullptr};
    torch::nn::BatchNorm2d policyBn{nullptr};
    torch::nn::Linear policyFc{nullptr};
    torch::nn::Conv2d valueConv{nullptr};
    torch::nn::BatchNorm2d valueBn{nullptr};
    torch::nn::Linear valueFc1{nullptr}, valueFc2{nullptr};

    int actionSize_;
    int boardCells_;
};
TORCH_MODULE(AlphaZeroNet);

struct InferenceResult {
    std::vector<float> policy;  // softmax over the full action space
    float value = 0.f;
};

// Thread-safe batching inference server. Self-play workers submit encoded
// states; a dedicated thread batches them and runs the network.
class InferenceServer {
public:
    InferenceServer(AlphaZeroNet net, torch::Device device, int inputPlanes,
                    int height, int width, int actionSize, int maxBatch,
                    int timeoutUs);
    ~InferenceServer();

    // Blocking call from worker threads.
    InferenceResult infer(const std::vector<float>& encodedState);

    // Swap in fresh weights (thread-safe).
    void updateWeights(AlphaZeroNet newNet);

    void stop();

private:
    struct Request {
        std::vector<float> input;
        std::promise<InferenceResult> promise;
    };

    void loop();

    AlphaZeroNet net_;
    torch::Device device_;
    int inputPlanes_, height_, width_, actionSize_, maxBatch_, timeoutUs_;

    std::mutex mu_;
    std::condition_variable cv_;
    std::queue<std::unique_ptr<Request>> queue_;
    std::atomic<bool> stop_{false};
    std::mutex netMu_;
    std::thread worker_;
};

}  // namespace hexgame