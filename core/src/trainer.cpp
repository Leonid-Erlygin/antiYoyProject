#include "trainer.hpp"

#include <filesystem>
#include <iostream>

namespace hexgame {

namespace fs = std::filesystem;

Trainer::Trainer(const TrainingConfig& cfg)
    : cfg_(cfg),
      device_(cfg.device == "cuda" && torch::cuda::is_available()
                  ? torch::Device(torch::kCUDA)
                  : torch::Device(torch::kCPU)),
      actions_(cfg.game) {
    torch::manual_seed(cfg_.seed);

    bestNet_ = AlphaZeroNet(cfg_.game, cfg_.network, actions_.size());
    candidateNet_ = AlphaZeroNet(cfg_.game, cfg_.network, actions_.size());

    // candidate starts as a copy of best
    {
        torch::NoGradGuard g;
        auto src = bestNet_->named_parameters(true);
        auto dst = candidateNet_->named_parameters(true);
        for (auto& item : src) dst[item.key()].copy_(item.value());
    }
    candidateNet_->to(device_);

    optimizer_ = std::make_unique<torch::optim::Adam>(
        candidateNet_->parameters(),
        torch::optim::AdamOptions(cfg_.network.learningRate)
            .weight_decay(cfg_.network.weightDecay));

    server_ = std::make_unique<InferenceServer>(
        bestNet_, device_, plane::kNumPlanes, cfg_.game.height, cfg_.game.width,
        actions_.size(), cfg_.selfPlay.inferenceBatchSize,
        cfg_.selfPlay.inferenceTimeoutUs);

    buffer_ = std::make_unique<ReplayBuffer>(cfg_.replayBuffer.capacity,
                                             cfg_.seed ^ 0xdeadbeefULL);

    fs::create_directories(cfg_.outputDir);
    fs::create_directories(fs::path(cfg_.outputDir) / cfg_.training.checkpointDir);
}

void Trainer::trainEpoch(int iteration) {
    candidateNet_->train();
    const int H = cfg_.game.height, W = cfg_.game.width;
    const size_t stateSize = static_cast<size_t>(plane::kNumPlanes) * H * W;
    const int A = actions_.size();

    double policyLossSum = 0, valueLossSum = 0;
    int batches = 0;

    for (int b = 0; b < cfg_.training.batchesPerIteration; ++b) {
        auto batch = buffer_->sample(cfg_.training.batchSize);
        if (batch.empty()) break;
        const int B = static_cast<int>(batch.size());

        torch::Tensor states = torch::empty({B, plane::kNumPlanes, H, W});
        torch::Tensor policies = torch::empty({B, A});
        torch::Tensor values = torch::empty({B, 1});
        float* sPtr = states.data_ptr<float>();
        float* pPtr = policies.data_ptr<float>();
        float* vPtr = values.data_ptr<float>();
        for (int i = 0; i < B; ++i) {
            std::copy(batch[i].state.begin(), batch[i].state.end(),
                      sPtr + static_cast<size_t>(i) * stateSize);
            std::copy(batch[i].policy.begin(), batch[i].policy.end(),
                      pPtr + static_cast<size_t>(i) * A);
            vPtr[i] = batch[i].value;
        }

        states = states.to(device_);
        policies = policies.to(device_);
        values = values.to(device_);

        optimizer_->zero_grad();
        auto [logits, value] = candidateNet_->forward(states);
        auto logSoftmax = torch::log_softmax(logits, 1);
        auto policyLoss = -(policies * logSoftmax).sum(1).mean();
        auto valueLoss = torch::mse_loss(value, values);
        auto loss = policyLoss + valueLoss;
        loss.backward();
        torch::nn::utils::clip_grad_norm_(candidateNet_->parameters(), 5.0);
        optimizer_->step();

        policyLossSum += policyLoss.item<double>();
        valueLossSum += valueLoss.item<double>();
        ++batches;
        ++trainSteps_;

        // lr decay
        if (trainSteps_ % cfg_.network.lrDecaySteps == 0) {
            for (auto& group : optimizer_->param_groups()) {
                auto& opts = static_cast<torch::optim::AdamOptions&>(group.options());
                opts.lr(opts.lr() * cfg_.network.lrDecayRate);
            }
        }
    }
    if (batches > 0) {
        std::cout << "[iter " << iteration << "] policy_loss="
                  << policyLossSum / batches
                  << " value_loss=" << valueLossSum / batches
                  << " buffer=" << buffer_->size() << std::endl;
    }
}

double Trainer::evaluateCandidate(uint64_t seedBase) {
    // candidate plays vs best. We run two servers and alternate colors.
    InferenceServer candidateServer(
        candidateNet_, device_, plane::kNumPlanes, cfg_.game.height,
        cfg_.game.width, actions_.size(), cfg_.selfPlay.inferenceBatchSize,
        cfg_.selfPlay.inferenceTimeoutUs);

    std::atomic<int> candidateWins{0}, games{0};
    std::atomic<int> nextGame{0};
    const int totalGames = cfg_.evaluation.games;

    auto playMatch = [&](int gameIdx) {
        const bool candidateIsFirst = gameIdx % 2 == 0;
        const uint64_t seed = seedBase + gameIdx * 104729ULL;

        GameState state(cfg_.game, seed);
        state.generateRandomGame();
        GameRules rules(state);
        const int cells = cfg_.game.height * cfg_.game.width;
        std::vector<uint8_t> unitMoved(cells, 0);
        rules.updateBeforeMove();

        MctsConfig evalMcts = cfg_.mcts;
        evalMcts.dirichletEpsilon = 0.0;
        Mcts mctsCand(cfg_.game, evalMcts, actions_, &candidateServer, seed);
        Mcts mctsBest(cfg_.game, evalMcts, actions_, server_.get(), seed ^ 1);

        int moveCount = 0;
        const long long microCap =
            static_cast<long long>(cfg_.game.maxMoves) * cells * 4;
        long long micro = 0;
        int result = 0;
        while (micro++ < microCap) {
            const int player = state.activePlayer();
            const bool candTurn = (player == 0) == candidateIsFirst;
            Mcts& mcts = candTurn ? mctsCand : mctsBest;
            auto visits = mcts.search(state, unitMoved, false);
            const int flat = mcts.selectAction(visits, 0.0);
            const Action act = actions_.decode(flat);
            const bool ended = actions_.apply(state, rules, act, unitMoved);
            if (ended) {
                ++moveCount;
                std::fill(unitMoved.begin(), unitMoved.end(), 0);
                rules.updateBeforeMove();
                const GameResult end = rules.checkGameEnd();
                if (end == GameResult::ActivePlayerLost) {
                    const int winner = 1 - state.activePlayer();
                    result = winner == 0 ? 1 : -1;
                    break;
                }
                if (end == GameResult::Draw || moveCount >= cfg_.game.maxMoves) {
                    result = 0;
                    break;
                }
            }
        }
        const int candResult = candidateIsFirst ? result : -result;
        if (candResult > 0) ++candidateWins;
        ++games;
    };

    std::vector<std::thread> threads;
    const int workers = std::min(cfg_.selfPlay.parallelWorkers, totalGames);
    for (int w = 0; w < workers; ++w) {
        threads.emplace_back([&] {
            while (true) {
                const int g = nextGame.fetch_add(1);
                if (g >= totalGames) break;
                playMatch(g);
            }
        });
    }
    for (auto& t : threads) t.join();
    candidateServer.stop();

    return games > 0 ? static_cast<double>(candidateWins) / games : 0.0;
}

void Trainer::saveCheckpoint(const std::string& path) {
    torch::save(bestNet_, path);
}

void Trainer::loadCheckpoint(const std::string& path) {
    torch::load(bestNet_, path);
    torch::NoGradGuard g;
    auto src = bestNet_->named_parameters(true);
    auto dst = candidateNet_->named_parameters(true);
    for (auto& item : src) dst[item.key()].copy_(item.value().to(device_));
    server_->updateWeights(bestNet_);
}

void Trainer::run() {
    SelfPlayEngine selfPlay(cfg_, actions_, server_.get(), buffer_.get());

    for (int iter = 1; iter <= cfg_.training.iterations; ++iter) {
        // ---- 1. self-play ----
        const auto t0 = std::chrono::steady_clock::now();
        SelfPlayStats stats = selfPlay.run(cfg_.seed + iter * 1000003ULL);
        const auto t1 = std::chrono::steady_clock::now();
        const double secs =
            std::chrono::duration<double>(t1 - t0).count();
        std::cout << "[iter " << iter << "] self-play: "
                  << stats.gamesFinished << " games, "
                  << stats.firstPlayerWins << " P1 wins, " << stats.draws
                  << " draws, " << stats.totalMoves << " samples in " << secs
                  << "s" << std::endl;

        // ---- 2. optimization ----
        if (buffer_->size() >= cfg_.replayBuffer.minSizeToTrain) {
            trainEpoch(iter);
        } else {
            std::cout << "[iter " << iter << "] buffer too small ("
                      << buffer_->size() << "), skipping training" << std::endl;
        }

        // ---- 3. evaluation / promotion ----
        if (cfg_.evaluation.enabled &&
            iter % cfg_.evaluation.everyIterations == 0 &&
            buffer_->size() >= cfg_.replayBuffer.minSizeToTrain) {
            const double winRate = evaluateCandidate(cfg_.seed + iter * 7717ULL);
            std::cout << "[iter " << iter << "] candidate win-rate: " << winRate
                      << std::endl;
            if (winRate >= cfg_.evaluation.winRateToPromote) {
                std::cout << "[iter " << iter << "] promoting candidate -> best"
                          << std::endl;
                torch::NoGradGuard g;
                auto src = candidateNet_->named_parameters(true);
                auto dst = bestNet_->named_parameters(true);
                for (auto& item : src)
                    dst[item.key()].copy_(item.value().to(torch::kCPU));
                auto srcB = candidateNet_->named_buffers(true);
                auto dstB = bestNet_->named_buffers(true);
                for (auto& item : srcB)
                    dstB[item.key()].copy_(item.value().to(torch::kCPU));
                server_->updateWeights(bestNet_);

                const auto bestPath = fs::path(cfg_.outputDir) /
                                      cfg_.training.checkpointDir /
                                      "best_model.pt";
                saveCheckpoint(bestPath.string());
            }
        }

        // ---- 4. checkpointing ----
        if (iter % cfg_.training.checkpointEvery == 0) {
            const auto path = fs::path(cfg_.outputDir) /
                              cfg_.training.checkpointDir /
                              ("model_iter_" + std::to_string(iter) + ".pt");
            saveCheckpoint(path.string());
            std::cout << "[iter " << iter << "] checkpoint saved: " << path
                      << std::endl;
        }
    }
    server_->stop();
}

}  // namespace hexgame