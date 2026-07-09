#pragma once
// ---------------------------------------------------------------------------
// Game visualizer: renders a GameState to SVG (vector) or PPM (raster).
// Mirrors the layout of the original draw_game (hex grid, per-player colors,
// unit / building glyphs).
// ---------------------------------------------------------------------------

#include <string>

#include "game_state.hpp"

namespace hexgame {

class Visualizer {
public:
    Visualizer(double hexRadiusPx, const std::string& format);

    // Renders `gs` to `path` (extension appended automatically).
    // Returns the full file path written.
    std::string render(const GameState& gs, const std::string& pathNoExt) const;

private:
    std::string renderSvg(const GameState& gs, const std::string& path) const;
    std::string renderPpm(const GameState& gs, const std::string& path) const;

    double r_;
    std::string format_;
};

}  // namespace hexgame