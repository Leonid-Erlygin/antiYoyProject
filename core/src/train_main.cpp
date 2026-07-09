// ---------------------------------------------------------------------------
// Entry point for AlphaZero training.
// Usage: ./train [path/to/training.yaml]
// ---------------------------------------------------------------------------

#include <iostream>

#include "config.hpp"
#include "trainer.hpp"

int main(int argc, char** argv) {
    std::string configPath = "configs/training.yaml";
    if (argc > 1) configPath = argv[1];

    try {
        auto cfg = hexgame::TrainingConfig::load(configPath);
        std::cout << "Loaded training config from " << configPath << std::endl;
        std::cout << "  board: " << cfg.game.height << "x" << cfg.game.width
                  << ", move_size=" << cfg.game.moveSize << std::endl;
        std::cout << "  device: " << cfg.device
                  << " (cuda available: " << torch::cuda::is_available() << ")"
                  << std::endl;
        std::cout << "  self-play: " << cfg.selfPlay.gamesPerIteration
                  << " games/iter, " << cfg.selfPlay.parallelWorkers
                  << " workers" << std::endl;

        hexgame::Trainer trainer(cfg);
        trainer.run();
    } catch (const std::exception& e) {
        std::cerr << "Fatal: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}