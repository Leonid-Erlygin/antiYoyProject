#pragma once
// ---------------------------------------------------------------------------
// YAML configuration loading for training and visualization.
// ---------------------------------------------------------------------------

#include <string>

#include "game_state.hpp"

namespace hexgame {

struct NetworkConfig {
    int channels = 128;
    int blocks = 8;
    int valueHeadHidden = 256;
    double learningRate = 1e-3;
    double weightDecay = 1e-4;
    int lrDecaySteps = 100000;
    double lrDecayRate = 0.1;
};

struct MctsConfig {
    int simulations = 200;
    double cPuct = 1.5;
    double dirichletAlpha = 0.3;
    double dirichletEpsilon = 0.25;
    int temperatureMoves = 30;
    double virtualLoss = 3.0;
};

struct SelfPlayConfig {
    int gamesPerIteration = 256;
    int parallelWorkers = 16;
    int inferenceBatchSize = 64;
    int inferenceTimeoutUs = 500;
};

struct ReplayBufferConfig {
    size_t capacity = 500000;
    size_t minSizeToTrain = 10000;
};

struct TrainLoopConfig {
    int iterations = 1000;
    int batchSize = 512;
    int batchesPerIteration = 200;
    int checkpointEvery = 5;
    std::string checkpointDir = "checkpoints";
};

struct EvaluationConfig {
    bool enabled = true;
    int games = 40;
    int everyIterations = 5;
    double winRateToPromote = 0.55;
};

struct TrainingConfig {
    uint64_t seed = 42;
    std::string device = "cuda";
    std::string outputDir = "outputs/training";
    GameConfig game;
    NetworkConfig network;
    MctsConfig mcts;
    SelfPlayConfig selfPlay;
    ReplayBufferConfig replayBuffer;
    TrainLoopConfig training;
    EvaluationConfig evaluation;

    static TrainingConfig load(const std::string& path);
};

struct VisualizationConfig {
    uint64_t seed = 7;
    std::string outputDir = "outputs/visualization";
    GameConfig game;
    double hexRadiusPx = 24.0;
    int saveEveryMove = 1;
    std::string format = "svg";
    std::string firstPlayer = "mcts";
    std::string secondPlayer = "random";
    std::string modelCheckpoint;
    MctsConfig mcts;
    std::string device = "cpu";

    static VisualizationConfig load(const std::string& path);
};

}  // namespace hexgame