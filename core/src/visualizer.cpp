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

namespace hexgame
{

    namespace fs = std::filesystem;

    // ==========================================================================
    // Small RGBA image container + helpers
    // ==========================================================================
    namespace
    {

        struct RGB
        {
            int r, g, b;
        };

        // Colors copied from the Python draw_game():
        //   BLACK = (0, 0, 0), GRAY = (0.5, 0.5, 0.5)
        //   player 0 -> (0, 0, 0.5)  (dark blue)
        //   player 1 -> (0.5, 0, 0)  (dark red)
        constexpr RGB kBlack{0, 0, 0};
        constexpr RGB kGray{128, 128, 128};
        constexpr RGB kBlue{0, 0, 128};
        constexpr RGB kRed{128, 0, 0};
        constexpr RGB kWhite{255, 255, 255};
        constexpr RGB kGreen{30, 140, 60}; // tree overlay (ppm mode only)

        struct Image
        {
            int w = 0, h = 0;
            std::vector<uint8_t> px; // RGBA, row-major
            bool ok() const { return w > 0 && h > 0; }
        };

        Image loadImage(const fs::path &path)
        {
            Image img;
            int channels = 0;
            unsigned char *data =
                stbi_load(path.string().c_str(), &img.w, &img.h, &channels, 4);
            if (!data)
            {
                img.w = img.h = 0;
                return img;
            }
            img.px.assign(data, data + static_cast<size_t>(img.w) * img.h * 4);
            stbi_image_free(data);
            return img;
        }

        // Bilinear sample of an RGBA image at floating-point (u, v) in pixel space.
        inline void sampleBilinear(const Image &img, double u, double v, float out[4])
        {
            u = std::clamp(u, 0.0, static_cast<double>(img.w - 1));
            v = std::clamp(v, 0.0, static_cast<double>(img.h - 1));
            const int x0 = static_cast<int>(u);
            const int y0 = static_cast<int>(v);
            const int x1 = std::min(x0 + 1, img.w - 1);
            const int y1 = std::min(y0 + 1, img.h - 1);
            const double fx = u - x0, fy = v - y0;
            const uint8_t *p00 = &img.px[(static_cast<size_t>(y0) * img.w + x0) * 4];
            const uint8_t *p10 = &img.px[(static_cast<size_t>(y0) * img.w + x1) * 4];
            const uint8_t *p01 = &img.px[(static_cast<size_t>(y1) * img.w + x0) * 4];
            const uint8_t *p11 = &img.px[(static_cast<size_t>(y1) * img.w + x1) * 4];
            for (int c = 0; c < 4; ++c)
            {
                const double top = p00[c] * (1 - fx) + p10[c] * fx;
                const double bot = p01[c] * (1 - fx) + p11[c] * fx;
                out[c] = static_cast<float>(top * (1 - fy) + bot * fy);
            }
        }

        // Alpha-composite a scaled RGBA sprite onto an RGB canvas, centered at
        // (cx, cy) with target size (tw, th).
        void blitScaled(std::vector<uint8_t> &canvas, int cw, int ch, const Image &img,
                        double cx, double cy, double tw, double th)
        {
            if (!img.ok() || tw <= 0 || th <= 0)
                return;
            const double left = cx - tw / 2.0, top = cy - th / 2.0;
            const int x0 = std::max(0, static_cast<int>(std::floor(left)));
            const int y0 = std::max(0, static_cast<int>(std::floor(top)));
            const int x1 = std::min(cw, static_cast<int>(std::ceil(left + tw)));
            const int y1 = std::min(ch, static_cast<int>(std::ceil(top + th)));
            for (int y = y0; y < y1; ++y)
            {
                for (int x = x0; x < x1; ++x)
                {
                    const double u = (x + 0.5 - left) / tw * img.w - 0.5;
                    const double v = (y + 0.5 - top) / th * img.h - 0.5;
                    float s[4];
                    sampleBilinear(img, u, v, s);
                    const float a = s[3] / 255.0f;
                    if (a <= 0.004f)
                        continue;
                    uint8_t *dst = &canvas[(static_cast<size_t>(y) * cw + x) * 3];
                    for (int c = 0; c < 3; ++c)
                    {
                        dst[c] = static_cast<uint8_t>(s[c] * a + dst[c] * (1.0f - a));
                    }
                }
            }
        }

        // Fill a pointy-top regular hexagon (circumradius R) centered at (cx, cy).
        // A point (dx, dy) relative to the center is inside iff
        //   |dx| <= sqrt(3)/2 * R   and   |dy| <= R - |dx| / sqrt(3)
        void fillHexagon(std::vector<uint8_t> &canvas, int cw, int ch, double cx,
                         double cy, double R, RGB color)
        {
            const double halfW = std::sqrt(3.0) / 2.0 * R;
            const int x0 = std::max(0, static_cast<int>(std::floor(cx - halfW)));
            const int x1 = std::min(cw - 1, static_cast<int>(std::ceil(cx + halfW)));
            const int y0 = std::max(0, static_cast<int>(std::floor(cy - R)));
            const int y1 = std::min(ch - 1, static_cast<int>(std::ceil(cy + R)));
            const double invSqrt3 = 1.0 / std::sqrt(3.0);
            for (int y = y0; y <= y1; ++y)
            {
                const double dy = std::abs(y + 0.5 - cy);
                for (int x = x0; x <= x1; ++x)
                {
                    const double dx = std::abs(x + 0.5 - cx);
                    if (dx <= halfW && dy <= R - dx * invSqrt3)
                    {
                        uint8_t *dst = &canvas[(static_cast<size_t>(y) * cw + x) * 3];
                        dst[0] = static_cast<uint8_t>(color.r);
                        dst[1] = static_cast<uint8_t>(color.g);
                        dst[2] = static_cast<uint8_t>(color.b);
                    }
                }
            }
        }

        // Absolute-player cell color exactly as in the Python draw_game.
        RGB cellColor(const GameState &gs, const Hex &h)
        {
            const RGB activeColor = gs.activePlayer() == 0 ? kBlue : kRed;
            const RGB adversaryColor = gs.activePlayer() == 0 ? kRed : kBlue;
            if (gs.at(h, gs.activePlane(plane::kPlayerHexes)) == 1)
                return activeColor;
            if (gs.at(h, gs.adversaryPlane(plane::kPlayerHexes)) == 1)
                return adversaryColor;
            if (gs.at(h, plane::kGray) == 1)
                return kGray;
            return kBlack;
        }

        std::string glyphFor(const GameState &gs, const Hex &h)
        {
            const int ut = gs.unitType(h);
            if (ut != 0)
                return "U" + std::to_string(ut);
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
            if (gs.at(h, plane::kGraves) == 1)
                return "+";
            if (gs.at(h, plane::kPine) == 1)
                return "p";
            return "";
        }

    } // namespace

    // ==========================================================================
    // Sprite bundle (pimpl). Mirrors the `pictures` dict of the Python
    // draw_game: only entity sprites, no hex tiles / background textures.
    // ==========================================================================
    struct Visualizer::Sprites
    {
        Image units[4]; // man0 .. man3
        Image tower1;   // tower.png
        Image tower2;   // strong_tower.png
        Image ambar;    // farm1.png
        Image town;     // castle.png
        Image grave;    // grave.png
        Image pine;     // pine.png
        bool loaded = false;

        bool loadAll(const fs::path &root)
        {
            const fs::path fe = root / "field_elements";
            units[0] = loadImage(fe / "man0.png");
            units[1] = loadImage(fe / "man1.png");
            units[2] = loadImage(fe / "man2.png");
            units[3] = loadImage(fe / "man3.png");
            tower1 = loadImage(fe / "tower.png");
            tower2 = loadImage(fe / "strong_tower.png");
            ambar = loadImage(fe / "farm1.png");
            town = loadImage(fe / "castle.png");
            grave = loadImage(fe / "grave.png");
            pine = loadImage(fe / "pine.png");

            loaded = units[0].ok() && units[1].ok() && units[2].ok() &&
                     units[3].ok() && tower1.ok() && tower2.ok() && ambar.ok() &&
                     town.ok() && grave.ok() && pine.ok();
            return loaded;
        }
    };

    // ==========================================================================
    // Visualizer
    // ==========================================================================
    Visualizer::Visualizer(const RenderOptions &opts)
        : opts_(opts), sprites_(std::make_unique<Sprites>()), r_(opts.hexRadiusPx)
    {
        if (opts_.mode == "assets")
        {
            if (opts_.assetsPath.empty() ||
                !sprites_->loadAll(fs::path(opts_.assetsPath)))
            {
                std::cerr << "[visualizer] warning: failed to load assets from '"
                          << opts_.assetsPath
                          << "', falling back to vector (svg) rendering"
                          << std::endl;
                opts_.mode = "vector";
                if (opts_.format == "png")
                    opts_.format = "svg";
            }
        }
    }

    Visualizer::~Visualizer() = default;

    std::string Visualizer::render(const GameState &gs,
                                   const std::string &pathNoExt) const
    {
        if (opts_.mode == "assets" && sprites_->loaded)
            return renderAssets(gs, pathNoExt + ".png");
        if (opts_.format == "ppm")
            return renderPpm(gs, pathNoExt + ".ppm");
        return renderSvg(gs, pathNoExt + ".svg");
    }

    // ==========================================================================
    // Asset-based PNG rendering — follows the Python draw_game():
    //   1. flat-colored regular hexagons on a white background
    //      (RegularPolyCollection equivalent),
    //   2. entity sprites (units, buildings, trees, graves) composited on top,
    //      one per hex, roughly hex-sized.
    // Rendered with supersampling for clean polygon edges, then downsampled.
    // ==========================================================================
    std::string Visualizer::renderAssets(const GameState &gs,
                                         const std::string &path) const
    {
        const auto &geo = gs.geometry();
        const int H = geo.height(), W = geo.width();
        constexpr int kSS = 3; // supersampling factor

        // board extents in base-resolution pixels
        const double margin = 1.5 * r_;
        double maxX = 0, maxY = 0;
        for (int row = 0; row < H; ++row)
            for (int col = 0; col < W; ++col)
            {
                auto [x, y] = geo.pixelCoordinates(Hex(row, col), r_);
                maxX = std::max(maxX, x);
                maxY = std::max(maxY, y);
            }
        const int outW = static_cast<int>(std::ceil(maxX + 2 * margin));
        const int outH = static_cast<int>(std::ceil(maxY + 2 * margin));
        const int cw = outW * kSS, ch = outH * kSS;

        // white background, as in matplotlib's default figure
        std::vector<uint8_t> canvas(static_cast<size_t>(cw) * ch * 3, 255);

        const double Rss = r_ * kSS;
        // slight inflation so adjacent hexes leave no background seams
        const double Rfill = Rss * 1.02;

        // pixel-space center of a hex; the y-axis is flipped so the output
        // matches matplotlib's y-up orientation
        auto hexCenter = [&](const Hex &h)
        {
            auto [x, y] = geo.pixelCoordinates(h, r_);
            const double cx = (x + margin) * kSS;
            const double cy = ch - (y + margin) * kSS;
            return std::make_pair(cx, cy);
        };

        // ---- pass 1: flat-colored hexagon cells ----
        for (int row = 0; row < H; ++row)
        {
            for (int col = 0; col < W; ++col)
            {
                const Hex h(row, col);
                auto [cx, cy] = hexCenter(h);
                fillHexagon(canvas, cw, ch, cx, cy, Rfill, cellColor(gs, h));
            }
        }

        // ---- pass 2: entity sprites (same entity set as the Python version) ----
        for (int row = 0; row < H; ++row)
        {
            for (int col = 0; col < W; ++col)
            {
                const Hex h(row, col);
                if (gs.at(h, plane::kBlack) == 1)
                    continue;

                const Image *sprite = nullptr;
                const int ut = gs.unitType(h);
                if (ut >= 1 && ut <= 4)
                {
                    sprite = &sprites_->units[ut - 1];
                }
                else if (gs.at(h, gs.activePlane(plane::kTown)) == 1 ||
                         gs.at(h, gs.adversaryPlane(plane::kTown)) == 1)
                {
                    sprite = &sprites_->town;
                }
                else if (gs.at(h, gs.activePlane(plane::kTower2)) == 1 ||
                         gs.at(h, gs.adversaryPlane(plane::kTower2)) == 1)
                {
                    sprite = &sprites_->tower2;
                }
                else if (gs.at(h, gs.activePlane(plane::kTower1)) == 1 ||
                         gs.at(h, gs.adversaryPlane(plane::kTower1)) == 1)
                {
                    sprite = &sprites_->tower1;
                }
                else if (gs.at(h, gs.activePlane(plane::kAmbar)) == 1 ||
                         gs.at(h, gs.adversaryPlane(plane::kAmbar)) == 1)
                {
                    sprite = &sprites_->ambar;
                }
                else if (gs.at(h, plane::kGraves) == 1)
                {
                    sprite = &sprites_->grave;
                }
                else if (gs.at(h, plane::kPine) == 1)
                {
                    sprite = &sprites_->pine;
                }
                if (!sprite || !sprite->ok())
                    continue;

                auto [cx, cy] = hexCenter(h);
                // fit the sprite inside the hexagon, preserving aspect ratio
                const double maxH = 1.45 * Rss;                 // hex height is 2R
                const double maxW = std::sqrt(3.0) * Rss * 0.9; // hex width
                const double aspect =
                    static_cast<double>(sprite->w) / std::max(1, sprite->h);
                double sh = maxH, sw = maxH * aspect;
                if (sw > maxW)
                {
                    sw = maxW;
                    sh = maxW / aspect;
                }
                // small upward nudge so sprites sit visually centered
                blitScaled(canvas, cw, ch, *sprite, cx, cy - 0.08 * Rss, sw, sh);
            }
        }

        // ---- downsample kSS x kSS -> output resolution (box filter) ----
        std::vector<uint8_t> out(static_cast<size_t>(outW) * outH * 3);
        const int area = kSS * kSS;
        for (int y = 0; y < outH; ++y)
        {
            for (int x = 0; x < outW; ++x)
            {
                int acc[3] = {0, 0, 0};
                for (int sy = 0; sy < kSS; ++sy)
                {
                    const uint8_t *srcRow =
                        &canvas[(static_cast<size_t>(y * kSS + sy) * cw +
                                 static_cast<size_t>(x) * kSS) *
                                3];
                    for (int sx = 0; sx < kSS; ++sx)
                    {
                        acc[0] += srcRow[sx * 3 + 0];
                        acc[1] += srcRow[sx * 3 + 1];
                        acc[2] += srcRow[sx * 3 + 2];
                    }
                }
                uint8_t *dst = &out[(static_cast<size_t>(y) * outW + x) * 3];
                dst[0] = static_cast<uint8_t>(acc[0] / area);
                dst[1] = static_cast<uint8_t>(acc[1] / area);
                dst[2] = static_cast<uint8_t>(acc[2] / area);
            }
        }

        stbi_write_png(path.c_str(), outW, outH, 3, out.data(), outW * 3);
        return path;
    }

    // ==========================================================================
    // Vector SVG rendering
    // ==========================================================================
    std::string Visualizer::renderSvg(const GameState &gs,
                                      const std::string &path) const
    {
        const auto &geo = gs.geometry();
        const int H = geo.height(), W = geo.width();

        const double margin = r_ * 2;
        double maxX = 0, maxY = 0;
        for (int row = 0; row < H; ++row)
        {
            for (int col = 0; col < W; ++col)
            {
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
        svg << "<rect width=\"100%\" height=\"100%\" fill=\"#ffffff\"/>\n";

        for (int row = 0; row < H; ++row)
        {
            for (int col = 0; col < W; ++col)
            {
                const Hex h(row, col);
                auto [cx, cy] = geo.pixelCoordinates(h, r_);
                cx += margin;
                cy = heightPx - (cy + margin); // match matplotlib's y-up

                const RGB c = cellColor(gs, h);
                svg << "<polygon points=\"";
                for (int k = 0; k < 6; ++k)
                {
                    const double a = M_PI / 6.0 + k * M_PI / 3.0;
                    svg << cx + r_ * std::cos(a) << "," << cy + r_ * std::sin(a)
                        << " ";
                }
                svg << "\" fill=\"rgb(" << c.r << "," << c.g << "," << c.b
                    << ")\"/>\n";

                const std::string glyph = glyphFor(gs, h);
                if (!glyph.empty())
                {
                    const bool isTree = glyph == "p";
                    svg << "<text x=\"" << cx << "\" y=\"" << cy + r_ * 0.25
                        << "\" font-size=\"" << r_ * 0.7
                        << "\" font-family=\"monospace\" text-anchor=\"middle\" "
                        << "fill=\"" << (isTree ? "rgb(30,200,60)" : "white")
                        << "\">" << glyph << "</text>\n";
                }
            }
        }
        svg << "</svg>\n";

        std::ofstream out(path);
        out << svg.str();
        return path;
    }

    // ==========================================================================
    // Raster PPM rendering
    // ==========================================================================
    std::string Visualizer::renderPpm(const GameState &gs,
                                      const std::string &path) const
    {
        const auto &geo = gs.geometry();
        const int H = geo.height(), W = geo.width();
        const double margin = r_ * 2;

        double maxX = 0, maxY = 0;
        for (int row = 0; row < H; ++row)
            for (int col = 0; col < W; ++col)
            {
                auto [x, y] = geo.pixelCoordinates(Hex(row, col), r_);
                maxX = std::max(maxX, x);
                maxY = std::max(maxY, y);
            }
        const int widthPx = static_cast<int>(maxX + 2 * margin);
        const int heightPx = static_cast<int>(maxY + 2 * margin);

        std::vector<RGB> img(static_cast<size_t>(widthPx) * heightPx, kWhite);

        auto setPx = [&](int x, int y, RGB c)
        {
            if (x >= 0 && x < widthPx && y >= 0 && y < heightPx)
                img[static_cast<size_t>(y) * widthPx + x] = c;
        };

        for (int row = 0; row < H; ++row)
        {
            for (int col = 0; col < W; ++col)
            {
                const Hex h(row, col);
                auto [cx, cy] = geo.pixelCoordinates(h, r_);
                cx += margin;
                cy = heightPx - (cy + margin);
                RGB c = cellColor(gs, h);
                if (gs.at(h, plane::kPine) == 1)
                    c = kGreen;

                const int rad = static_cast<int>(r_ * 0.9);
                for (int dy = -rad; dy <= rad; ++dy)
                {
                    for (int dx = -rad; dx <= rad; ++dx)
                    {
                        if (dx * dx + dy * dy <= rad * rad)
                        {
                            setPx(static_cast<int>(cx) + dx, static_cast<int>(cy) + dy, c);
                        }
                    }
                }
                if (gs.unitType(h) != 0)
                {
                    const int ur = std::max(2, static_cast<int>(r_ * 0.25));
                    for (int dy = -ur; dy <= ur; ++dy)
                        for (int dx = -ur; dx <= ur; ++dx)
                            if (dx * dx + dy * dy <= ur * ur)
                                setPx(static_cast<int>(cx) + dx,
                                      static_cast<int>(cy) + dy, RGB{40, 40, 40});
                }
            }
        }

        std::ofstream out(path, std::ios::binary);
        out << "P6\n"
            << widthPx << " " << heightPx << "\n255\n";
        for (const RGB &p : img)
        {
            out.put(static_cast<char>(p.r));
            out.put(static_cast<char>(p.g));
            out.put(static_cast<char>(p.b));
        }
        return path;
    }

} // namespace hexgame