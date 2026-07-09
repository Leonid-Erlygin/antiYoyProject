#include "visualizer.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#include <stb_image.h>
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include <stb_image_write.h>

namespace hexgame {

namespace fs = std::filesystem;

// ==========================================================================
// Small RGBA image container + helpers
// ==========================================================================
namespace {

struct RGB {
    int r, g, b;
};

constexpr RGB kBlack{20, 20, 20};
constexpr RGB kGray{128, 128, 128};
constexpr RGB kBlue{40, 70, 200};   // player 0
constexpr RGB kRed{200, 50, 50};    // player 1
constexpr RGB kGreen{30, 140, 60};  // tree overlay (ppm mode)
constexpr RGB kWaterFallback{14, 40, 66};

struct Image {
    int w = 0, h = 0;
    std::vector<uint8_t> px;  // RGBA, row-major
    bool ok() const { return w > 0 && h > 0; }
};

Image loadImage(const fs::path& path) {
    Image img;
    int channels = 0;
    unsigned char* data =
        stbi_load(path.string().c_str(), &img.w, &img.h, &channels, 4);
    if (!data) {
        img.w = img.h = 0;
        return img;
    }
    img.px.assign(data, data + static_cast<size_t>(img.w) * img.h * 4);
    stbi_image_free(data);
    return img;
}

// Bilinear sample of an RGBA image at floating-point (u, v) in pixel space.
inline void sampleBilinear(const Image& img, double u, double v, float out[4]) {
    u = std::clamp(u, 0.0, static_cast<double>(img.w - 1));
    v = std::clamp(v, 0.0, static_cast<double>(img.h - 1));
    const int x0 = static_cast<int>(u);
    const int y0 = static_cast<int>(v);
    const int x1 = std::min(x0 + 1, img.w - 1);
    const int y1 = std::min(y0 + 1, img.h - 1);
    const double fx = u - x0, fy = v - y0;
    const uint8_t* p00 = &img.px[(static_cast<size_t>(y0) * img.w + x0) * 4];
    const uint8_t* p10 = &img.px[(static_cast<size_t>(y0) * img.w + x1) * 4];
    const uint8_t* p01 = &img.px[(static_cast<size_t>(y1) * img.w + x0) * 4];
    const uint8_t* p11 = &img.px[(static_cast<size_t>(y1) * img.w + x1) * 4];
    for (int c = 0; c < 4; ++c) {
        const double top = p00[c] * (1 - fx) + p10[c] * fx;
        const double bot = p01[c] * (1 - fx) + p11[c] * fx;
        out[c] = static_cast<float>(top * (1 - fy) + bot * fy);
    }
}

// Alpha-composite a scaled RGBA sprite onto an RGB canvas, centered at
// (cx, cy) with target size (tw, th).
void blitScaled(std::vector<uint8_t>& canvas, int cw, int ch, const Image& img,
                double cx, double cy, double tw, double th) {
    if (!img.ok() || tw <= 0 || th <= 0) return;
    const double left = cx - tw / 2.0, top = cy - th / 2.0;
    const int x0 = std::max(0, static_cast<int>(std::floor(left)));
    const int y0 = std::max(0, static_cast<int>(std::floor(top)));
    const int x1 = std::min(cw, static_cast<int>(std::ceil(left + tw)));
    const int y1 = std::min(ch, static_cast<int>(std::ceil(top + th)));
    for (int y = y0; y < y1; ++y) {
        for (int x = x0; x < x1; ++x) {
            const double u = (x + 0.5 - left) / tw * img.w - 0.5;
            const double v = (y + 0.5 - top) / th * img.h - 0.5;
            float s[4];
            sampleBilinear(img, u, v, s);
            const float a = s[3] / 255.0f;
            if (a <= 0.004f) continue;
            uint8_t* dst = &canvas[(static_cast<size_t>(y) * cw + x) * 3];
            for (int c = 0; c < 3; ++c) {
                dst[c] = static_cast<uint8_t>(s[c] * a + dst[c] * (1.0f - a));
            }
        }
    }
}

// ---- tiny 3x5 bitmap digit font (for money labels) ----
constexpr uint8_t kDigits[10][5] = {
    {0b111, 0b101, 0b101, 0b101, 0b111},  // 0
    {0b010, 0b110, 0b010, 0b010, 0b111},  // 1
    {0b111, 0b001, 0b111, 0b100, 0b111},  // 2
    {0b111, 0b001, 0b111, 0b001, 0b111},  // 3
    {0b101, 0b101, 0b111, 0b001, 0b001},  // 4
    {0b111, 0b100, 0b111, 0b001, 0b111},  // 5
    {0b111, 0b100, 0b111, 0b101, 0b111},  // 6
    {0b111, 0b001, 0b010, 0b010, 0b010},  // 7
    {0b111, 0b101, 0b111, 0b101, 0b111},  // 8
    {0b111, 0b101, 0b111, 0b001, 0b111},  // 9
};

void drawRect(std::vector<uint8_t>& canvas, int cw, int ch, int x, int y,
              int w, int h, RGB color) {
    for (int yy = std::max(0, y); yy < std::min(ch, y + h); ++yy) {
        for (int xx = std::max(0, x); xx < std::min(cw, x + w); ++xx) {
            uint8_t* dst = &canvas[(static_cast<size_t>(yy) * cw + xx) * 3];
            dst[0] = static_cast<uint8_t>(color.r);
            dst[1] = static_cast<uint8_t>(color.g);
            dst[2] = static_cast<uint8_t>(color.b);
        }
    }
}

// Draws `value` starting at (x, y); returns width consumed in pixels.
int drawNumber(std::vector<uint8_t>& canvas, int cw, int ch, int x, int y,
               int scale, int value, RGB color, RGB shadow) {
    const std::string s = std::to_string(value);
    int cursor = x;
    for (char c : s) {
        if (c < '0' || c > '9') {
            cursor += 2 * scale;
            continue;
        }
        const uint8_t* rows = kDigits[c - '0'];
        for (int ry = 0; ry < 5; ++ry) {
            for (int rx = 0; rx < 3; ++rx) {
                if (rows[ry] & (1 << (2 - rx))) {
                    drawRect(canvas, cw, ch, cursor + rx * scale + 1,
                             y + ry * scale + 1, scale, scale, shadow);
                    drawRect(canvas, cw, ch, cursor + rx * scale,
                             y + ry * scale, scale, scale, color);
                }
            }
        }
        cursor += 4 * scale;
    }
    return cursor - x;
}

RGB cellColor(const GameState& gs, const Hex& h) {
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

// ==========================================================================
// Sprite bundle (pimpl)
// ==========================================================================
struct Visualizer::Sprites {
    Image hexBlue;     // player 0 tile
    Image hexRed;      // player 1 tile
    Image hexNeutral;  // gray (unowned land) tile
    Image water;       // tiled background
    Image units[4];    // man0..man3
    Image tower1, tower2, farm, town, grave, pine, coin;
    bool loaded = false;

    bool loadAll(const fs::path& root) {
        hexBlue = loadImage(root / "hex_blue.png");
        hexRed = loadImage(root / "hex_red.png");
        hexNeutral = loadImage(root / "hex_black.png");
        water = loadImage(root / "game_background_water.png");
        const fs::path fe = root / "field_elements";
        units[0] = loadImage(fe / "man0.png");
        units[1] = loadImage(fe / "man1.png");
        units[2] = loadImage(fe / "man2.png");
        units[3] = loadImage(fe / "man3.png");
        tower1 = loadImage(fe / "tower.png");
        tower2 = loadImage(fe / "strong_tower.png");
        farm = loadImage(fe / "farm1.png");
        town = loadImage(fe / "castle.png");
        grave = loadImage(fe / "grave.png");
        pine = loadImage(fe / "pine.png");
        coin = loadImage(root / "coin.png");

        loaded = hexBlue.ok() && hexRed.ok() && hexNeutral.ok() &&
                 units[0].ok() && units[1].ok() && units[2].ok() &&
                 units[3].ok() && tower1.ok() && tower2.ok() && farm.ok() &&
                 town.ok() && grave.ok() && pine.ok();
        return loaded;
    }
};

// ==========================================================================
// Visualizer
// ==========================================================================
Visualizer::Visualizer(const RenderOptions& opts)
    : opts_(opts), sprites_(std::make_unique<Sprites>()), r_(opts.hexRadiusPx) {
    if (opts_.mode == "assets") {
        if (opts_.assetsPath.empty() ||
            !sprites_->loadAll(fs::path(opts_.assetsPath))) {
            std::cerr << "[visualizer] warning: failed to load assets from '"
                      << opts_.assetsPath
                      << "', falling back to vector (svg) rendering"
                      << std::endl;
            opts_.mode = "vector";
            if (opts_.format == "png") opts_.format = "svg";
        }
    }
}

Visualizer::~Visualizer() = default;

std::string Visualizer::render(const GameState& gs,
                               const std::string& pathNoExt) const {
    if (opts_.mode == "assets" && sprites_->loaded)
        return renderAssets(gs, pathNoExt + ".png");
    if (opts_.format == "ppm") return renderPpm(gs, pathNoExt + ".ppm");
    return renderSvg(gs, pathNoExt + ".svg");
}

// ==========================================================================
// Asset-based PNG rendering
// ==========================================================================
std::string Visualizer::renderAssets(const GameState& gs,
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
    const int cw = static_cast<int>(maxX + 2 * margin);
    const int ch = static_cast<int>(maxY + 2 * margin);

    std::vector<uint8_t> canvas(static_cast<size_t>(cw) * ch * 3);

    // ---- background: tiled water texture (or flat fallback color) ----
    const Image& water = sprites_->water;
    if (water.ok()) {
        for (int y = 0; y < ch; ++y) {
            for (int x = 0; x < cw; ++x) {
                const uint8_t* src =
                    &water.px[(static_cast<size_t>(y % water.h) * water.w +
                               (x % water.w)) * 4];
                uint8_t* dst = &canvas[(static_cast<size_t>(y) * cw + x) * 3];
                dst[0] = src[0];
                dst[1] = src[1];
                dst[2] = src[2];
            }
        }
    } else {
        for (int i = 0; i < cw * ch; ++i) {
            canvas[i * 3 + 0] = kWaterFallback.r;
            canvas[i * 3 + 1] = kWaterFallback.g;
            canvas[i * 3 + 2] = kWaterFallback.b;
        }
    }

    // pointy-top hexagon bounding box: width = sqrt(3)*r, height = 2*r
    const double tileW = std::sqrt(3.0) * r_ * 1.02;
    const double tileH = 2.0 * r_ * 1.02;

    // ---- pass 1: hex tiles ----
    for (int row = 0; row < H; ++row) {
        for (int col = 0; col < W; ++col) {
            const Hex h(row, col);
            if (gs.at(h, plane::kBlack) == 1) continue;  // water
            auto [cx, cy] = geo.pixelCoordinates(h, r_);
            cx += margin;
            cy += margin;

            const Image* tile = &sprites_->hexNeutral;
            const bool activeOwns =
                gs.at(h, gs.activePlane(plane::kPlayerHexes)) == 1;
            const bool adversaryOwns =
                gs.at(h, gs.adversaryPlane(plane::kPlayerHexes)) == 1;
            if (activeOwns) {
                tile = gs.activePlayer() == 0 ? &sprites_->hexBlue
                                              : &sprites_->hexRed;
            } else if (adversaryOwns) {
                tile = gs.activePlayer() == 0 ? &sprites_->hexRed
                                              : &sprites_->hexBlue;
            }
            blitScaled(canvas, cw, ch, *tile, cx, cy, tileW, tileH);
        }
    }

    // ---- pass 2: entities (units, buildings, trees, graves) ----
    for (int row = 0; row < H; ++row) {
        for (int col = 0; col < W; ++col) {
            const Hex h(row, col);
            if (gs.at(h, plane::kBlack) == 1) continue;
            auto [cx, cy] = geo.pixelCoordinates(h, r_);
            cx += margin;
            cy += margin;

            const Image* sprite = nullptr;
            const int ut = gs.unitType(h);
            if (ut >= 1 && ut <= 4) {
                sprite = &sprites_->units[ut - 1];
            } else if (gs.at(h, gs.activePlane(plane::kTown)) == 1 ||
                       gs.at(h, gs.adversaryPlane(plane::kTown)) == 1) {
                sprite = &sprites_->town;
            } else if (gs.at(h, gs.activePlane(plane::kTower2)) == 1 ||
                       gs.at(h, gs.adversaryPlane(plane::kTower2)) == 1) {
                sprite = &sprites_->tower2;
            } else if (gs.at(h, gs.activePlane(plane::kTower1)) == 1 ||
                       gs.at(h, gs.adversaryPlane(plane::kTower1)) == 1) {
                sprite = &sprites_->tower1;
            } else if (gs.at(h, gs.activePlane(plane::kAmbar)) == 1 ||
                       gs.at(h, gs.adversaryPlane(plane::kAmbar)) == 1) {
                sprite = &sprites_->farm;
            } else if (gs.at(h, plane::kGraves) == 1) {
                sprite = &sprites_->grave;
            } else if (gs.at(h, plane::kPine) == 1) {
                sprite = &sprites_->pine;
            }
            if (!sprite || !sprite->ok()) continue;

            // scale sprite to fit inside the hex, preserving aspect ratio
            const double box = 1.25 * r_;
            const double aspect =
                static_cast<double>(sprite->w) / std::max(1, sprite->h);
            double sw = box, sh = box;
            if (aspect > 1.0) sh = box / aspect;
            else sw = box * aspect;
            blitScaled(canvas, cw, ch, *sprite, cx, cy, sw, sh);
        }
    }

    // ---- pass 3: money labels on province towns (coin + digits) ----
    const int digitScale = std::max(1, static_cast<int>(r_ / 12.0));
    for (int row = 0; row < H; ++row) {
        for (int col = 0; col < W; ++col) {
            const Hex h(row, col);
            const bool activeTown = gs.at(h, gs.activePlane(plane::kTown)) == 1;
            const bool adversaryTown =
                gs.at(h, gs.adversaryPlane(plane::kTown)) == 1;
            if (!activeTown && !adversaryTown) continue;

            const int money =
                activeTown ? gs.at(h, gs.activePlane(plane::kMoney))
                           : gs.at(h, gs.adversaryPlane(plane::kMoney));
            auto [cx, cy] = geo.pixelCoordinates(h, r_);
            cx += margin;
            cy += margin;

            const double coinSize = 0.45 * r_;
            double x = cx - 0.55 * r_;
            const double yTop = cy + 0.45 * r_;
            if (sprites_->coin.ok()) {
                blitScaled(canvas, cw, ch, sprites_->coin,
                           x + coinSize / 2.0, yTop + coinSize / 2.0, coinSize,
                           coinSize);
                x += coinSize + 2;
            }
            drawNumber(canvas, cw, ch, static_cast<int>(x),
                       static_cast<int>(yTop), digitScale, money,
                       RGB{255, 215, 0}, RGB{40, 30, 0});
        }
    }

    stbi_write_png(path.c_str(), cw, ch, 3, canvas.data(), cw * 3);
    return path;
}

// ==========================================================================
// Vector SVG rendering (unchanged behaviour)
// ==========================================================================
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

// ==========================================================================
// Raster PPM rendering (unchanged behaviour)
// ==========================================================================
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

            const int rad = static_cast<int>(r_ * 0.9);
            for (int dy = -rad; dy <= rad; ++dy) {
                for (int dx = -rad; dx <= rad; ++dx) {
                    if (dx * dx + dy * dy <= rad * rad) {
                        setPx(static_cast<int>(cx) + dx, static_cast<int>(cy) + dy, c);
                    }
                }
            }
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