// ---------------------------------------------------------------------------
// Entry point for game visualization.
// Plays one game (random vs random, mcts vs random, or mcts vs mcts as
// configured) and renders each position to disk.
// Usage: ./visualize [path/to/visualization.yaml]
// ---------------------------------------------------------------------------

#include <filesystem>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>

#include "action_space.hpp"
#include "config.hpp"
#include "game_rules.hpp"
#include "mcts.hpp"
#include "neural_net.hpp"
#include "visualizer.hpp"

namespace fs = std::filesystem;
using namespace hexgame;

namespace
{

    // Uniform-random legal micro-action policy (baseline player).
    int randomAction(const std::vector<uint8_t> &legal, std::mt19937_64 &rng)
    {
        std::vector<int> candidates;
        for (int i = 0; i < static_cast<int>(legal.size()); ++i)
            if (legal[i])
                candidates.push_back(i);
        if (candidates.empty())
            return static_cast<int>(legal.size()) - 1;
        std::uniform_int_distribution<size_t> d(0, candidates.size() - 1);
        return candidates[d(rng)];
    }

} // namespace

int main(int argc, char **argv)
{
    std::string configPath = "configs/visualization.yaml";
    if (argc > 1)
        configPath = argv[1];

    try
    {
        auto cfg = VisualizationConfig::load(configPath);
        fs::create_directories(cfg.outputDir);

        ActionSpace actions(cfg.game);

        RenderOptions renderOpts;
        renderOpts.hexRadiusPx = cfg.hexRadiusPx;
        renderOpts.format = cfg.format;
        renderOpts.mode = cfg.renderMode;
        renderOpts.assetsPath = cfg.assetsPath;
        Visualizer viz(renderOpts);

        // optional network
        std::unique_ptr<InferenceServer> server;
        AlphaZeroNet net{nullptr};
        const bool needsNet =
            cfg.firstPlayer == "mcts" || cfg.secondPlayer == "mcts";
        if (needsNet)
        {
            NetworkConfig netCfg; // architecture defaults must match training
            net = AlphaZeroNet(cfg.game, netCfg, actions.size());
            if (!cfg.modelCheckpoint.empty() && fs::exists(cfg.modelCheckpoint))
            {
                torch::load(net, cfg.modelCheckpoint);
                std::cout << "Loaded checkpoint: " << cfg.modelCheckpoint
                          << std::endl;
            }
            else
            {
                std::cout << "Warning: no checkpoint found at '"
                          << cfg.modelCheckpoint
                          << "', using randomly initialized network"
                          << std::endl;
            }
            const torch::Device device(
                cfg.device == "cuda" && torch::cuda::is_available()
                    ? torch::kCUDA
                    : torch::kCPU);
            server = std::make_unique<InferenceServer>(
                net, device, plane::kNumPlanes, cfg.game.height, cfg.game.width,
                actions.size(), 8, 200);
        }

        // ---- play one game, rendering as we go ----
        GameState state(cfg.game, cfg.seed);
        state.generateRandomGame();
        GameRules rules(state);
        std::mt19937_64 rng(cfg.seed ^ 0xabcdef);

        MctsConfig playCfg = cfg.mcts;
        playCfg.dirichletEpsilon = 0.0;
        std::unique_ptr<Mcts> mcts;
        if (server)
        {
            mcts = std::make_unique<Mcts>(cfg.game, playCfg, actions,
                                          server.get(), cfg.seed);
        }

        const int cells = cfg.game.height * cfg.game.width;
        std::vector<uint8_t> unitMoved(cells, 0);
        rules.updateBeforeMove();

        auto renderFrame = [&](int frame)
        {
            std::ostringstream name;
            name << "frame_" << std::setw(5) << std::setfill('0') << frame;
            const auto path =
                viz.render(state, (fs::path(cfg.outputDir) / name.str()).string());
            return path;
        };
        int frame = 0;
        renderFrame(frame++);

        int moveCount = 0;
        const long long microCap =
            static_cast<long long>(cfg.game.maxMoves) * cells * 4;
        long long micro = 0;
        int result = 0;
        bool over = false;

        while (!over && micro++ < microCap)
        {
            const int player = state.activePlayer();
            const std::string &strategy =
                player == 0 ? cfg.firstPlayer : cfg.secondPlayer;

            int flat;
            if (strategy == "mcts" && mcts)
            {
                auto visits = mcts->search(state, unitMoved, false);
                flat = mcts->selectAction(
                    visits, moveCount < cfg.mcts.temperatureMoves ? 1.0 : 0.0);
            }
            else
            {
                const auto legal = actions.legalMask(state, rules, unitMoved);
                flat = randomAction(legal, rng);
            }

            const Action act = actions.decode(flat);
            const bool ended = actions.apply(state, rules, act, unitMoved);

            if (ended)
            {
                ++moveCount;
                if (moveCount % cfg.saveEveryMove == 0)
                {
                    std::cout << "move " << moveCount << " -> "
                              << renderFrame(frame++) << std::endl;
                }
                std::fill(unitMoved.begin(), unitMoved.end(), 0);
                rules.updateBeforeMove();
                const GameResult end = rules.checkGameEnd();
                if (end == GameResult::ActivePlayerLost)
                {
                    const int winner = 1 - state.activePlayer();
                    result = winner == 0 ? 1 : -1;
                    over = true;
                }
                else if (end == GameResult::Draw ||
                         moveCount >= cfg.game.maxMoves)
                {
                    result = 0;
                    over = true;
                }
            }
        }

        renderFrame(frame++);
        if (result > 0)
            std::cout << "Player 1 wins";
        else if (result < 0)
            std::cout << "Player 2 wins";
        else
            std::cout << "Draw";
        std::cout << " after " << moveCount << " moves. Frames written to "
                  << cfg.outputDir << std::endl;

        if (server)
            server->stop();
    }
    catch (const std::exception &e)
    {
        std::cerr << "Fatal: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}