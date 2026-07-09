# Hex AlphaZero (C++)

Complete C++ rewrite of the hex-strategy game engine with an AlphaZero-style
training pipeline.

## Components

| Piece | Description |
|---|---|
| `hex_engine` | Game logic (map generation, provinces, units, economy) — faithful port of the Python `engine/` package |
| `hex_rl` | Residual policy/value network (LibTorch), batched inference server, PUCT MCTS, parallel self-play, replay buffer, training loop |
| `hex_viz` | SVG / PPM renderer for game states |
| `train` | Training entry point, configured by `configs/training.yaml` |
| `visualize` | Plays and renders a game, configured by `configs/visualization.yaml` |

## Action space

A turn is decomposed into micro-actions so that MCTS has a tractable
branching factor:

- **UNIT_MOVE(cell, target)** — move the unit at `cell` to one of the
  T reachable targets ($T = 19$ for `move_size: 2`, $T = 61$ for `move_size: 4`)
- **SPEND(cell, action)** — buy unit 1–4 / tower 1–2 / barn on `cell`
- **END_TURN** — finish the turn (also covers "do nothing")

Total flat action size: $H \cdot W \cdot T + H \cdot W \cdot 7 + 1$.

## Parallelism

- N self-play worker threads each run their own game + MCTS.
- All workers submit positions to a single **batched inference server**
  which coalesces requests (configurable batch size / timeout) and runs
  the network on GPU — this is where the throughput comes from.
- The replay buffer and weight updates are fully thread-safe.

## Build

Requirements: CMake ≥ 3.18, a C++17 compiler, LibTorch.

```bash
cd core
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$(python -c 'import torch; print(torch.utils.cmake_prefix_path)')" \
  -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build -j8
```


# training
./train configs/training.yaml

# visualization (renders frames into outputs/visualization)
./visualize configs/visualization.yaml

Convert frames to a video:
ffmpeg -framerate 4 -i outputs/visualization/frame_%05d.svg game.mp4


## Design Notes

**Game logic fidelity.** All rules are ported directly from the Python engine: starvation and income accrual (`update_before_move`), graves→trees, tree growth (`update_after_move`), unit merging with income adjustments, province merging/splitting with BFS detection, town relocation (`find_place_for_new_town`), barn cost escalation, defence calculations, and the exact hex adjacency and `compute_hex_by_layer` coordinate math.

**Key improvement over the old code.** The Python engine sampled *distributions over entire turn plans* (movement order, spend order, etc.), which is intractable for MCTS. The new pipeline decomposes a turn into **micro-actions** (move one unit / one purchase / end turn) — this gives a well-defined flat action space of size $H \cdot W \cdot T + 7 \cdot H \cdot W + 1$ that the policy head can predict directly, while preserving the full expressiveness of a turn (any sequence of moves and purchases in any order).

**Value convention.** The value head outputs $v \in [-1, 1]$ from the *active player's* perspective; MCTS backups negate $v$ across player switches, and training targets are $z = \pm 1$ (win/loss) or $0$ (draw, including the 500-step no-expansion stall rule from the original `game_end_check`).

**Throughput.** Self-play workers are CPU-bound on game logic and MCTS tree operations, while the GPU is saturated via the batching inference server — this is the standard architecture that lets a single GPU serve dozens of self-play threads.