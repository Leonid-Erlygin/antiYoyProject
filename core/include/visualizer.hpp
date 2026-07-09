#pragma once
// ---------------------------------------------------------------------------
// Game visualizer.
//
// Two rendering modes:
//   - "assets": composites the original game sprites (hex tiles, units,
//     buildings, trees, coins) into a PNG frame. Requires assets_path.
//   - "vector": self-contained SVG or PPM output (no external files).
// ---------------------------------------------------------------------------

#include <memory>
#include <string>

#include "game_state.hpp"

namespace hexgame {

struct RenderOptions {
    double hexRadiusPx = 32.0;
    std::string format = "png";   // png (assets) | svg | ppm (vector)
    std::string mode = "assets";  // assets | vector
    std::string assetsPath;       // root of the game assets directory
};

class Visualizer {
public:
    explicit Visualizer(const RenderOptions& opts);
    ~Visualizer();

    Visualizer(const Visualizer&) = delete;
    Visualizer& operator=(const Visualizer&) = delete;

    // Renders `gs` to `pathNoExt` (extension appended automatically).
    // Returns the full file path written.
    std::string render(const GameState& gs, const std::string& pathNoExt) const;

private:
    std::string renderSvg(const GameState& gs, const std::string& path) const;
    std::string renderPpm(const GameState& gs, const std::string& path) const;
    std::string renderAssets(const GameState& gs, const std::string& path) const;

    RenderOptions opts_;
    struct Sprites;  // pimpl: keeps stb_image out of the header
    std::unique_ptr<Sprites> sprites_;
    double r_;
};

}  // namespace hexgame