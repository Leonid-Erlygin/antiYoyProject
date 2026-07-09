#pragma once
// ---------------------------------------------------------------------------
// Hexagonal coordinate system. Faithful port of the Python
// engine/coordinate_system_operations.py and GameState adjacency logic.
//
// The board uses "offset" coordinates (row, col) with odd-column shifting,
// identical to the original engine.
// ---------------------------------------------------------------------------

#include <array>
#include <cstdint>
#include <optional>
#include <utility>
#include <vector>

namespace hexgame {

struct Hex {
    int16_t row = -1;
    int16_t col = -1;

    Hex() = default;
    Hex(int r, int c) : row(static_cast<int16_t>(r)), col(static_cast<int16_t>(c)) {}

    bool operator==(const Hex& o) const { return row == o.row && col == o.col; }
    bool operator!=(const Hex& o) const { return !(*this == o); }
    bool operator<(const Hex& o) const {
        return row < o.row || (row == o.row && col < o.col);
    }
    bool valid() const { return row >= 0 && col >= 0; }
};

struct HexHash {
    size_t operator()(const Hex& h) const {
        return (static_cast<size_t>(static_cast<uint16_t>(h.row)) << 16) |
               static_cast<uint16_t>(h.col);
    }
};

// Number of target cells for a unit move given the movement range.
// move_size == 4 -> 61 cells,  move_size == 2 -> 19 cells.
inline constexpr int kMoveTargets4 = 61;
inline constexpr int kMoveTargets2 = 19;
// Index of "stay in place" within the 61-cell layout (as in the Python code).
inline constexpr int kStayIndex61 = 30;
// Index of "stay in place" within the 19-cell layout.
inline constexpr int kStayIndex19 = 9;

class HexGeometry {
public:
    HexGeometry(int height, int width);

    int height() const { return height_; }
    int width() const { return width_; }
    int numCells() const { return height_ * width_; }

    int index(const Hex& h) const { return h.row * width_ + h.col; }
    Hex fromIndex(int idx) const { return Hex(idx / width_, idx % width_); }

    // Adjacent hex in one of 6 directions; std::nullopt if off-board.
    // Direction numbering is identical to the Python getAdjacentHex.
    std::optional<Hex> adjacent(const Hex& h, int direction) const;

    // All valid neighbours of a hex.
    std::vector<Hex> adjacentAll(const Hex& h) const;

    // Port of compute_hex_by_layer: maps a move index i (0..60) plus an
    // origin hex to the destination hex (may be off-board -> nullopt).
    std::optional<Hex> hexByLayer61(int i, const Hex& origin) const;

    // 19-cell layout used when move_size == 2: the origin plus its two rings.
    // Index kStayIndex19 corresponds to the origin itself.
    std::optional<Hex> hexByLayer19(int i, const Hex& origin) const;

    // Dispatch based on number of targets (19 or 61).
    std::optional<Hex> hexByLayer(int i, const Hex& origin, int numTargets) const;

    // Euclidean pixel coordinates of a hexagon centre (used for rendering
    // and island-road generation), identical to computeCoordinates.
    std::pair<double, double> pixelCoordinates(const Hex& h, double r) const;

    // Inverse of pixelCoordinates (identical to getHexByPos).
    Hex hexByPixel(double x, double y, double r) const;

private:
    int height_;
    int width_;
};

}  // namespace hexgame