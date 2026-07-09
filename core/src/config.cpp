#include "config.hpp"

#include <yaml-cpp/yaml.h>

namespace hexgame {

namespace {

GameConfig loadGame(const YAML::Node& n) {
    GameConfig g;
    if (!n) return g;
    if (n["width"]) g.width = n["width"].as<int>();
    if (n["height"]) g.height = n["height"].as<int>();
    if (n["move_size"]) g.moveSize = n["move_size"].as<int>();
    if (n["max_moves"]) g.maxMoves = n["max_moves"].as<int>();
    if (n["islands"]) g.islands = n["islands"].as<int>();
    if (n["island_size"]) g.islandSize = n["island_size"].as<int>();
    if (n["tree_probability"]) g.treeProbability = n["tree_probability"].as<double>();
    if (n["tree_growth_probability"])
        g.treeGrowthProbability = n["tree_growth_probability"].as<double>();
    return g;
}

MctsConfig loadMcts(const YAML::Node& n) {
    MctsConfig m;
    if (!n) return m;
    if (n["simulations"]) m.simulations = n["simulations"].as<int>();
    if (n["c_puct"]) m.cPuct = n["c_puct"].as<double>();
    if (n["dirichlet_alpha"]) m.dirichletAlpha = n["dirichlet_alpha"].as<double>();
    if (n["dirichlet_epsilon"])
        m.dirichletEpsilon = n["dirichlet_epsilon"].as<double>();
    if (n["temperature_moves"]) m.temperatureMoves = n["temperature_moves"].as<int>();
    if (n["virtual_loss"]) m.virtualLoss = n["virtual_loss"].as<double>();
    return m;
}

}  // namespace

TrainingConfig TrainingConfig::load(const std::string& path) {
    YAML::Node root = YAML::LoadFile(path);
    TrainingConfig c;
    if (root["seed"]) c.seed = root["seed"].as<uint64_t>();
    if (root["device"]) c.device = root["device"].as<std::string>();
    if (root["output_dir"]) c.outputDir = root["output_dir"].as<std::string>();
    c.game = loadGame(root["game"]);
    c.mcts = loadMcts(root["mcts"]);

    if (auto n = root["network"]) {
        if (n["channels"]) c.network.channels = n["channels"].as<int>();
        if (n["blocks"]) c.network.blocks = n["blocks"].as<int>();
        if (n["value_head_hidden"])
            c.network.valueHeadHidden = n["value_head_hidden"].as<int>();
        if (n["learning_rate"]) c.network.learningRate = n["learning_rate"].as<double>();
        if (n["weight_decay"]) c.network.weightDecay = n["weight_decay"].as<double>();
        if (n["lr_decay_steps"]) c.network.lrDecaySteps = n["lr_decay_steps"].as<int>();
        if (n["lr_decay_rate"]) c.network.lrDecayRate = n["lr_decay_rate"].as<double>();
    }
    if (auto n = root["self_play"]) {
        if (n["games_per_iteration"])
            c.selfPlay.gamesPerIteration = n["games_per_iteration"].as<int>();
        if (n["parallel_workers"])
            c.selfPlay.parallelWorkers = n["parallel_workers"].as<int>();
        if (n["inference_batch_size"])
            c.selfPlay.inferenceBatchSize = n["inference_batch_size"].as<int>();
        if (n["inference_timeout_us"])
            c.selfPlay.inferenceTimeoutUs = n["inference_timeout_us"].as<int>();
    }
    if (auto n = root["replay_buffer"]) {
        if (n["capacity"]) c.replayBuffer.capacity = n["capacity"].as<size_t>();
        if (n["min_size_to_train"])
            c.replayBuffer.minSizeToTrain = n["min_size_to_train"].as<size_t>();
    }
    if (auto n = root["training"]) {
        if (n["iterations"]) c.training.iterations = n["iterations"].as<int>();
        if (n["batch_size"]) c.training.batchSize = n["batch_size"].as<int>();
        if (n["batches_per_iteration"])
            c.training.batchesPerIteration = n["batches_per_iteration"].as<int>();
        if (n["checkpoint_every"])
            c.training.checkpointEvery = n["checkpoint_every"].as<int>();
        if (n["checkpoint_dir"])
            c.training.checkpointDir = n["checkpoint_dir"].as<std::string>();
    }
    if (auto n = root["evaluation"]) {
        if (n["enabled"]) c.evaluation.enabled = n["enabled"].as<bool>();
        if (n["games"]) c.evaluation.games = n["games"].as<int>();
        if (n["every_iterations"])
            c.evaluation.everyIterations = n["every_iterations"].as<int>();
        if (n["win_rate_to_promote"])
            c.evaluation.winRateToPromote = n["win_rate_to_promote"].as<double>();
    }
    return c;
}

VisualizationConfig VisualizationConfig::load(const std::string& path) {
    YAML::Node root = YAML::LoadFile(path);
    VisualizationConfig c;
    if (root["seed"]) c.seed = root["seed"].as<uint64_t>();
    if (root["output_dir"]) c.outputDir = root["output_dir"].as<std::string>();
    c.game = loadGame(root["game"]);
    c.mcts = loadMcts(root["mcts"]);
    if (auto n = root["render"]) {
        if (n["mode"]) c.renderMode = n["mode"].as<std::string>();
        if (n["assets_path"]) c.assetsPath = n["assets_path"].as<std::string>();
        if (n["hex_radius_px"]) c.hexRadiusPx = n["hex_radius_px"].as<double>();
        if (n["save_every_move"]) c.saveEveryMove = n["save_every_move"].as<int>();
        if (n["format"]) c.format = n["format"].as<std::string>();
    }
    if (auto n = root["players"]) {
        if (n["first"]) c.firstPlayer = n["first"].as<std::string>();
        if (n["second"]) c.secondPlayer = n["second"].as<std::string>();
    }
    if (root["model_checkpoint"])
        c.modelCheckpoint = root["model_checkpoint"].as<std::string>();
    if (root["device"]) c.device = root["device"].as<std::string>();
    return c;
}

}  // namespace hexgame