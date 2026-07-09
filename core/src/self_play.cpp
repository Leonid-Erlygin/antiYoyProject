#include "self_play.hpp"

#include <atomic>
#include <thread>

namespace hexgame {

SelfPlayEngine::SelfPlayEngine(const TrainingConfig& cfg,
                               const ActionSpace& actions,
                               InferenceServer* server, ReplayBuffer* buffer)
    : cfg_(cfg), actions_(actions), server_(server), buffer_(buffer) {}

int SelfPlayEngine::playOneGame(
    uint64_t seed, bool collectSamples, std::vector<TrainingSample>* out,
    const std::function<void(const GameState&, int)>& onMove) {
    GameState state(cfg_.game, seed);
    state.generateRandomGame();
    GameRules rules(state);
    Mcts mcts(cfg_.game, cfg_.mcts, actions_, server_, seed ^ 0x9e3779b97f4a7c15ULL);

    struct PendingSample {
        std::vector<float> stateEnc;
        std::vector<float> policy;
        int player;
    };
    std::vector<PendingSample> pending;

    const int cells = cfg_.game.height * cfg_.game.width;
    std::vector<uint8_t> unitMoved(cells, 0);

    // first player's initial pre-move update
    rules.updateBeforeMove();

    int result = 0;  // from player 0's perspective
    int moveCount = 0;
    bool gameOver = false;
    // cap on micro-actions to guarantee termination
    const long long microCap =
        static_cast<long long>(cfg_.game.maxMoves) * cells * 4;
    long long microActions = 0;

    while (!gameOver && microActions < microCap) {
        ++microActions;
        const int player = state.activePlayer();

        const bool addNoise = collectSamples;
        auto visits = mcts.search(state, unitMoved, addNoise);

        if (collectSamples) {
            PendingSample s;
            s.stateEnc.resize(static_cast<size_t>(plane::kNumPlanes) *
                              cfg_.game.height * cfg_.game.width);
            state.encodeForNetwork(s.stateEnc.data());
            s.policy = visits;
            s.player = player;
            pending.push_back(std::move(s));
        }

        const double temp =
            moveCount < cfg_.mcts.temperatureMoves ? 1.0 : 0.0;
        const int flat = mcts.selectAction(visits, temp);
        const Action act = actions_.decode(flat);
        const bool turnEnded = actions_.apply(state, rules, act, unitMoved);

        if (onMove) onMove(state, moveCount);

        if (turnEnded) {
            ++moveCount;
            std::fill(unitMoved.begin(), unitMoved.end(), 0);
            rules.updateBeforeMove();
            const GameResult end = rules.checkGameEnd();
            if (end == GameResult::ActivePlayerLost) {
                // the active (about-to-move) player lost -> previous player won
                const int winner = 1 - state.activePlayer();
                result = winner == 0 ? 1 : -1;
                gameOver = true;
            } else if (end == GameResult::Draw ||
                       moveCount >= cfg_.game.maxMoves) {
                result = 0;
                gameOver = true;
            }
        }
    }

    if (collectSamples && out) {
        for (auto& p : pending) {
            TrainingSample s;
            s.state = std::move(p.stateEnc);
            s.policy = std::move(p.policy);
            s.value = p.player == 0 ? static_cast<float>(result)
                                    : static_cast<float>(-result);
            out->push_back(std::move(s));
        }
    }
    return result;
}

SelfPlayStats SelfPlayEngine::run(uint64_t seedBase) {
    std::atomic<int> gamesFinished{0};
    std::atomic<int> firstPlayerWins{0};
    std::atomic<int> draws{0};
    std::atomic<long long> totalMoves{0};

    std::atomic<int> nextGame{0};
    const int totalGames = cfg_.selfPlay.gamesPerIteration;
    const int workers = cfg_.selfPlay.parallelWorkers;

    auto workerFn = [&](int workerId) {
        while (true) {
            const int gameIdx = nextGame.fetch_add(1);
            if (gameIdx >= totalGames) break;
            std::vector<TrainingSample> samples;
            const uint64_t seed =
                seedBase + static_cast<uint64_t>(gameIdx) * 7919ULL +
                static_cast<uint64_t>(workerId);
            const int result = playOneGame(seed, /*collectSamples=*/true, &samples);
            totalMoves.fetch_add(static_cast<long long>(samples.size()));
            buffer_->add(std::move(samples));
            gamesFinished.fetch_add(1);
            if (result > 0) firstPlayerWins.fetch_add(1);
            if (result == 0) draws.fetch_add(1);
        }
    };

    std::vector<std::thread> threads;
    threads.reserve(workers);
    for (int w = 0; w < workers; ++w) threads.emplace_back(workerFn, w);
    for (auto& t : threads) t.join();

    SelfPlayStats stats;
    stats.gamesFinished = gamesFinished.load();
    stats.firstPlayerWins = firstPlayerWins.load();
    stats.draws = draws.load();
    stats.totalMoves = totalMoves.load();
    return stats;
}

}  // namespace hexgame