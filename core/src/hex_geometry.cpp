#include "hex_geometry.hpp"

#include <cmath>

namespace hexgame {

namespace {

// base_hexes from coordinate_system_operations.py:
// per-layer relative offsets; [even_col_variant, odd_col_variant]
struct LayerBase {
    int evenDr, evenDc;
    int oddDr, oddDc;
};

constexpr std::array<LayerBase, 9> kBaseHexes = {{
    {-2, -4, -2, -4},  // i < 5
    {-3, -3, -2, -3},  // i < 11
    {-3, -2, -3, -2},  // i < 18
    {-4, -1, -3, -1},  // i < 26
    {-4, 0, -4, 0},    // i < 35
    {-4, 1, -3, 1},    // i < 43
    {-3, 2, -3, 2},    // i < 50
    {-3, 3, -2, 3},    // i < 56
    {-2, 4, -2, 4},    // i < 61
}};

constexpr std::array<int, 9> kLayerStarts = {0, 5, 11, 18, 26, 35, 43, 50, 56};
constexpr std::array<int, 9> kLayerEnds = {5, 11, 18, 26, 35, 43, 50, 56, 61};

}  // namespace

HexGeometry::HexGeometry(int height, int width) : height_(height), width_(width) {}

std::optional<Hex> HexGeometry::adjacent(const Hex& h, int direction) const {
    const int r = h.row, c = h.col;
    const bool oddCol = (c % 2) == 1;
    switch (direction) {
        case 0:
            if (c == 0) return std::nullopt;
            if (r == 0 && !oddCol) return std::nullopt;
            return oddCol ? Hex(r, c - 1) : Hex(r - 1, c - 1);
        case 1:
            if (r == 0) return std::nullopt;
            return Hex(r - 1, c);
        case 2:
            if (c == width_ - 1) return std::nullopt;
            if (r == 0 && !oddCol) return std::nullopt;
            return oddCol ? Hex(r, c + 1) : Hex(r - 1, c + 1);
        case 3:
            if (c == width_ - 1) return std::nullopt;
            if (r == height_ - 1 && oddCol) return std::nullopt;
            return !oddCol ? Hex(r, c + 1) : Hex(r + 1, c + 1);
        case 4:
            if (r == height_ - 1) return std::nullopt;
            return Hex(r + 1, c);
        case 5:
            if (c == 0 || (r == height_ - 1 && oddCol)) return std::nullopt;
            return oddCol ? Hex(r + 1, c - 1) : Hex(r, c - 1);
        default:
            return std::nullopt;
    }
}

std::vector<Hex> HexGeometry::adjacentAll(const Hex& h) const {
    std::vector<Hex> out;
    out.reserve(6);
    for (int d = 0; d < 6; ++d) {
        if (auto a = adjacent(h, d)) out.push_back(*a);
    }
    return out;
}

std::optional<Hex> HexGeometry::hexByLayer61(int i, const Hex& origin) const {
    if (i < 0 || i >= kMoveTargets4) return std::nullopt;
    const bool odd = (origin.col % 2) != 0;

    int layer = 0;
    for (int l = 0; l < 9; ++l) {
        if (i < kLayerEnds[l]) {
            layer = l;
            break;
        }
    }
    const auto& b = kBaseHexes[layer];
    const int dr = odd ? b.oddDr : b.evenDr;
    const int dc = odd ? b.oddDc : b.evenDc;
    const int row = dr + origin.row + (i - kLayerStarts[layer]);
    const int col = origin.col + dc;

    if (row < 0 || row >= height_ || col < 0 || col >= width_) return std::nullopt;
    return Hex(row, col);
}

std::optional<Hex> HexGeometry::hexByLayer19(int i, const Hex& origin) const {
    // The 19-cell disk is the sub-disk of the 61-cell layout that corresponds
    // to distance <= 2. Within the 61-cell layout those are the indices with
    // hex-distance(origin, target) <= 2. We enumerate them in a fixed order.
    //
    // Fixed mapping (computed once): the two inner rings of the 61-disk.
    // Ordering is by 61-index for determinism.
    static const std::array<int, kMoveTargets2> kDiskIndices = {
        // distance <= 2 subset of the 61-layout (row-major inside the layout)
        12, 13, 14, 19, 20, 21, 22, 27, 28, 30, 31, 32, 36, 37, 38, 39, 44, 45, 46};
    if (i < 0 || i >= kMoveTargets2) return std::nullopt;
    return hexByLayer61(kDiskIndices[i], origin);
}

std::optional<Hex> HexGeometry::hexByLayer(int i, const Hex& origin,
                                           int numTargets) const {
    if (numTargets == kMoveTargets4) return hexByLayer61(i, origin);
    return hexByLayer19(i, origin);
}

std::pair<double, double> HexGeometry::pixelCoordinates(const Hex& h, double r) const {
    const double parity = (h.col % 2 == 0) ? 0.0 : 1.0;  // (1 - (-1)^col)/2
    const double x = r * std::sqrt(3.0) * h.row + r * parity * std::sqrt(3.0) / 2.0;
    const double y = r * 1.5 * h.col;
    return {x, y};
}

Hex HexGeometry::hexByPixel(double x, double y, double r) const {
    const int j = static_cast<int>((2.0 / (r * 3.0)) * y);
    const double parity = (j % 2 == 0) ? 0.0 : 1.0;
    const int i = static_cast<int>((x - r * parity * std::sqrt(3.0) / 2.0) /
                                   (r * std::sqrt(3.0)));
    if (i < 0 || i > height_ - 1 || j < 0 || j > width_ - 1) return Hex(0, 0);
    return Hex(i, j);
}

}  // namespace hexgame