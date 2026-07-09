#include "visualizer.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>
#include <vector>

namespace hexgame {

namespace {

struct RGB {
    int r, g, b;
};

constexpr RGB kBlack{20, 20, 20};
constexpr RGB kGray{128, 128, 128};
constexpr RGB kBlue{40, 70, 200};   // player 0
constexpr RGB kRed{200, 50, 50};    // player 1
constexpr RGB kGreen{30, 140, 60};  // tree overlay

RGB cellColor(const GameState& gs, const Hex& h) {
    // active player planes always describe the *current* active player;
    // map back to absolute player colors.
    const RGB activeColor = gs.activePlayer() == 0 ? kBlue : kRed;
    const RGB adversaryColor = gs.activePlayer() == 0 ? kRed : kBlue;
    if (gs.at(h, gs.activePlane(plane::kPlayerHexes)) == 1) return activeColor;
    if (gs.at(h, gs.adversaryPlane(plane::kPlayerHexes)) == 1)
        return adversaryColor;
    if (gs.at(h, plane::kGray) == 1) return kGray;
    return kBlack;
}

std::string glyphFor(const GameState& gs, const Hex& h) {
    const int ut = gs.unitType(h);
    if (ut != 0) return "U" + std::to_string(ut);
    if (gs.at(h, gs.activePlane(plane::kTown)) == 1 ||
        gs.at(h, gs.adversaryPlane(plane::kTown)) == 1)
        return "T";
    if (gs.at(h, gs.activePlane(plane::kTower2)) == 1 ||
        gs.at(h, gs.adversaryPlane(plane::kTower2)) == 1)
        return "W2";
    if (gs.at(h, gs.activePlane(plane::kTower1)) == 1 ||
        gs.at(h, gs.adversaryPlane(plane::kTower1)) == 1)
        return "W1";
    if (gs.at(h, gs.activePlane(plane::kAmbar)) == 1 ||
        gs.at(h, gs.adversaryPlane(plane::kAmbar)) == 1)
        return "B";
    if (gs.at(h, plane::kGraves) == 1) return "+";
    if (gs.at(h, plane::kPine) == 1) return "p";
    return "";
}

}  // namespace

Visualizer::Visualizer(double hexRadiusPx, const std::string& format)
    : r_(hexRadiusPx), format_(format) {}

std::string Visualizer::render(const GameState& gs,
                               const std::string& pathNoExt) const {
    if (format_ == "ppm") return renderPpm(gs, pathNoExt + ".ppm");
    return renderSvg(gs, pathNoExt + ".svg");
}

std::string Visualizer::renderSvg(const GameState& gs,
                                  const std::string& path) const {
    const auto& geo = gs.geometry();
    const int H = geo.height(), W = geo.width();

    const double margin = r_ * 2;
    double maxX = 0, maxY = 0;
    for (int row = 0; row < H; ++row) {
        for (int col = 0; col < W; ++col) {
            auto [x, y] = geo.pixelCoordinates(Hex(row, col), r_);
            maxX = std::max(maxX, x);
            maxY = std::max(maxY, y);
        }
    }
    const double widthPx = maxX + 2 * margin;
    const double heightPx = maxY + 2 * margin;

    std::ostringstream svg;
    svg << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
    svg << "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" << widthPx
        << "\" height=\"" << heightPx << "\" viewBox=\"0 0 " << widthPx << " "
        << heightPx << "\">\n";
    svg << "<rect width=\"100%\" height=\"100%\" fill=\"#0a0a1e\"/>\n";

    for (int row = 0; row < H; ++row) {
        for (int col = 0; col < W; ++col) {
            const Hex h(row, col);
            auto [cx, cy] = geo.pixelCoordinates(h, r_);
            cx += margin;
            cy += margin;

            const RGB c = cellColor(gs, h);
            // pointy-top hexagon (matches the coordinate layout)
            svg << "<polygon points=\"";
            for (int k = 0; k < 6; ++k) {
                const double a = M_PI / 6.0 + k * M_PI / 3.0;
                svg << cx + r_ * 0.95 * std::cos(a) << ","
                    << cy + r_ * 0.95 * std::sin(a) << " ";
            }
            svg << "\" fill=\"rgb(" << c.r << "," << c.g << "," << c.b
                << ")\" stroke=\"#222\" stroke-width=\"1\"/>\n";

            const std::string glyph = glyphFor(gs, h);
            if (!glyph.empty()) {
                const bool isTree = glyph == "p";
                svg << "<text x=\"" << cx << "\" y=\"" << cy + r_ * 0.25
                    << "\" font-size=\"" << r_ * 0.7
                    << "\" font-family=\"monospace\" text-anchor=\"middle\" "
                    << "fill=\"" << (isTree ? "rgb(30,200,60)" : "white")
                    << "\">" << glyph << "</text>\n";
            }

            // money annotation on province cells
            const int moneyA = gs.at(h, gs.activePlane(plane::kMoney));
            const int provA = gs.at(h, gs.activePlane(plane::kProvinceIndex));
            const int moneyB = gs.at(h, gs.adversaryPlane(plane::kMoney));
            const int provB = gs.at(h, gs.adversaryPlane(plane::kProvinceIndex));
            int money = 0;
            bool own = false;
            if (provA != 0) { money = moneyA; own = true; }
            else if (provB != 0) { money = moneyB; own = true; }
            if (own) {
                svg << "<text x=\"" << cx << "\" y=\"" << cy + r_ * 0.75
                    << "\" font-size=\"" << r_ * 0.4
                    << "\" font-family=\"monospace\" text-anchor=\"middle\" "
                       "fill=\"#ffd700\">"
                    << money << "</text>\n";
            }
        }
    }
    svg << "</svg>\n";

    std::ofstream out(path);
    out << svg.str();
    return path;
}

std::string Visualizer::renderPpm(const GameState& gs,
                                  const std::string& path) const {
    const auto& geo = gs.geometry();
    const int H = geo.height(), W = geo.width();
    const double margin = r_ * 2;

    double maxX = 0, maxY = 0;
    for (int row = 0; row < H; ++row)
        for (int col = 0; col < W; ++col) {
            auto [x, y] = geo.pixelCoordinates(Hex(row, col), r_);
            maxX = std::max(maxX, x);
            maxY = std::max(maxY, y);
        }
    const int widthPx = static_cast<int>(maxX + 2 * margin);
    const int heightPx = static_cast<int>(maxY + 2 * margin);

    std::vector<RGB> img(static_cast<size_t>(widthPx) * heightPx, RGB{10, 10, 30});

    auto setPx = [&](int x, int y, RGB c) {
        if (x >= 0 && x < widthPx && y >= 0 && y < heightPx)
            img[static_cast<size_t>(y) * widthPx + x] = c;
    };

    for (int row = 0; row < H; ++row) {
        for (int col = 0; col < W; ++col) {
            const Hex h(row, col);
            auto [cx, cy] = geo.pixelCoordinates(h, r_);
            cx += margin;
            cy += margin;
            RGB c = cellColor(gs, h);
            if (gs.at(h, plane::kPine) == 1) c = kGreen;

            // fill a hex-ish disk
            const int rad = static_cast<int>(r_ * 0.9);
            for (int dy = -rad; dy <= rad; ++dy) {
                for (int dx = -rad; dx <= rad; ++dx) {
                    if (dx * dx + dy * dy <= rad * rad) {
                        setPx(static_cast<int>(cx) + dx, static_cast<int>(cy) + dy, c);
                    }
                }
            }
            // unit marker: small white dot
            if (gs.unitType(h) != 0) {
                const int ur = std::max(2, static_cast<int>(r_ * 0.25));
                for (int dy = -ur; dy <= ur; ++dy)
                    for (int dx = -ur; dx <= ur; ++dx)
                        if (dx * dx + dy * dy <= ur * ur)
                            setPx(static_cast<int>(cx) + dx,
                                  static_cast<int>(cy) + dy, RGB{255, 255, 255});
            }
        }
    }

    std::ofstream out(path, std::ios::binary);
    out << "P6\n" << widthPx << " " << heightPx << "\n255\n";
    for (const RGB& p : img) {
        out.put(static_cast<char>(p.r));
        out.put(static_cast<char>(p.g));
        out.put(static_cast<char>(p.b));
    }
    return path;
}

}  // namespace hexgame