#include "neural_net.hpp"

#include <chrono>

namespace hexgame {

// ==========================================================================
// Network
// ==========================================================================
ResidualBlockImpl::ResidualBlockImpl(int channels) {
    conv1 = register_module(
        "conv1", torch::nn::Conv2d(
                     torch::nn::Conv2dOptions(channels, channels, 3).padding(1).bias(false)));
    bn1 = register_module("bn1", torch::nn::BatchNorm2d(channels));
    conv2 = register_module(
        "conv2", torch::nn::Conv2d(
                     torch::nn::Conv2dOptions(channels, channels, 3).padding(1).bias(false)));
    bn2 = register_module("bn2", torch::nn::BatchNorm2d(channels));
}

torch::Tensor ResidualBlockImpl::forward(torch::Tensor x) {
    auto out = torch::relu(bn1(conv1(x)));
    out = bn2(conv2(out));
    return torch::relu(out + x);
}

AlphaZeroNetImpl::AlphaZeroNetImpl(const GameConfig& game, const NetworkConfig& net,
                                   int actionSize)
    : actionSize_(actionSize), boardCells_(game.height * game.width) {
    stem = register_module(
        "stem", torch::nn::Conv2d(torch::nn::Conv2dOptions(plane::kNumPlanes,
                                                           net.channels, 3)
                                      .padding(1)
                                      .bias(false)));
    stemBn = register_module("stem_bn", torch::nn::BatchNorm2d(net.channels));
    blocks = register_module("blocks", torch::nn::ModuleList());
    for (int i = 0; i < net.blocks; ++i) blocks->push_back(ResidualBlock(net.channels));

    policyConv = register_module(
        "policy_conv",
        torch::nn::Conv2d(torch::nn::Conv2dOptions(net.channels, 32, 1).bias(false)));
    policyBn = register_module("policy_bn", torch::nn::BatchNorm2d(32));
    policyFc = register_module(
        "policy_fc", torch::nn::Linear(32 * boardCells_, actionSize));

    valueConv = register_module(
        "value_conv",
        torch::nn::Conv2d(torch::nn::Conv2dOptions(net.channels, 8, 1).bias(false)));
    valueBn = register_module("value_bn", torch::nn::BatchNorm2d(8));
    valueFc1 = register_module(
        "value_fc1", torch::nn::Linear(8 * boardCells_, net.valueHeadHidden));
    valueFc2 = register_module("value_fc2",
                               torch::nn::Linear(net.valueHeadHidden, 1));
}

std::pair<torch::Tensor, torch::Tensor> AlphaZeroNetImpl::forward(torch::Tensor x) {
    auto out = torch::relu(stemBn(stem(x)));
    for (auto& block : *blocks) {
        out = block->as<ResidualBlock>()->forward(out);
    }
    auto p = torch::relu(policyBn(policyConv(out)));
    p = p.flatten(1);
    p = policyFc(p);

    auto v = torch::relu(valueBn(valueConv(out)));
    v = v.flatten(1);
    v = torch::relu(valueFc1(v));
    v = torch::tanh(valueFc2(v));
    return {p, v};
}

// ==========================================================================
// InferenceServer
// ==========================================================================
InferenceServer::InferenceServer(AlphaZeroNet net, torch::Device device,
                                 int inputPlanes, int height, int width,
                                 int actionSize, int maxBatch, int timeoutUs)
    : net_(std::move(net)),
      device_(device),
      inputPlanes_(inputPlanes),
      height_(height),
      width_(width),
      actionSize_(actionSize),
      maxBatch_(maxBatch),
      timeoutUs_(timeoutUs) {
    net_->to(device_);
    net_->eval();
    worker_ = std::thread([this] { loop(); });
}

InferenceServer::~InferenceServer() { stop(); }

void InferenceServer::stop() {
    bool expected = false;
    if (stop_.compare_exchange_strong(expected, true)) {
        cv_.notify_all();
        if (worker_.joinable()) worker_.join();
    }
}

void InferenceServer::updateWeights(AlphaZeroNet newNet) {
    std::lock_guard<std::mutex> lock(netMu_);
    torch::NoGradGuard g;
    auto src = newNet->named_parameters(true);
    auto dst = net_->named_parameters(true);
    for (auto& item : src) {
        dst[item.key()].copy_(item.value().to(device_));
    }
    auto srcB = newNet->named_buffers(true);
    auto dstB = net_->named_buffers(true);
    for (auto& item : srcB) {
        dstB[item.key()].copy_(item.value().to(device_));
    }
}

InferenceResult InferenceServer::infer(const std::vector<float>& encodedState) {
    auto req = std::make_unique<Request>();
    req->input = encodedState;
    auto fut = req->promise.get_future();
    {
        std::lock_guard<std::mutex> lock(mu_);
        queue_.push(std::move(req));
    }
    cv_.notify_one();
    return fut.get();
}

void InferenceServer::loop() {
    const size_t inputSize =
        static_cast<size_t>(inputPlanes_) * height_ * width_;
    while (!stop_.load()) {
        std::vector<std::unique_ptr<Request>> batch;
        {
            std::unique_lock<std::mutex> lock(mu_);
            cv_.wait_for(lock, std::chrono::microseconds(timeoutUs_),
                         [this] { return !queue_.empty() || stop_.load(); });
            if (stop_.load()) break;
            while (!queue_.empty() &&
                   batch.size() < static_cast<size_t>(maxBatch_)) {
                batch.push_back(std::move(queue_.front()));
                queue_.pop();
            }
        }
        if (batch.empty()) continue;

        const int B = static_cast<int>(batch.size());
        torch::Tensor input = torch::empty(
            {B, inputPlanes_, height_, width_}, torch::kFloat32);
        float* dst = input.data_ptr<float>();
        for (int b = 0; b < B; ++b) {
            std::copy(batch[b]->input.begin(), batch[b]->input.end(),
                      dst + static_cast<size_t>(b) * inputSize);
        }

        torch::Tensor logits, value;
        {
            std::lock_guard<std::mutex> lock(netMu_);
            torch::NoGradGuard g;
            auto [l, v] = net_->forward(input.to(device_));
            logits = torch::softmax(l, /*dim=*/1).to(torch::kCPU).contiguous();
            value = v.to(torch::kCPU).contiguous();
        }

        const float* pol = logits.data_ptr<float>();
        const float* val = value.data_ptr<float>();
        for (int b = 0; b < B; ++b) {
            InferenceResult r;
            r.policy.assign(pol + static_cast<size_t>(b) * actionSize_,
                            pol + static_cast<size_t>(b + 1) * actionSize_);
            r.value = val[b];
            batch[b]->promise.set_value(std::move(r));
        }
    }
    // drain remaining requests with neutral answers
    std::lock_guard<std::mutex> lock(mu_);
    while (!queue_.empty()) {
        InferenceResult r;
        r.policy.assign(actionSize_, 1.0f / actionSize_);
        queue_.front()->promise.set_value(std::move(r));
        queue_.pop();
    }
}

}  // namespace hexgame