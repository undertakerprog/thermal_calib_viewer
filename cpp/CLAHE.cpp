#include "CLAHE.h"

#include <climits>
#include <iostream>

#include "../core/math.h"
#include "../core/mat_math.h"
#include "../core/watch.h"

using namespace eye;
using namespace imgproc;

void CLAHE::process(Mat<int16_t>& src, Mat<uint8_t>& dst) {
    int16_t min;
    int16_t max;

    Math::minMax(src, min, max);
    Math::sub(src, min);

    max = max - min;
    min = 0;

    auto bins = Math::alignHi(max + 1, 8);

    dst.create(src);

    uint16_t* pImage = (uint16_t*)src.first();
    uint32_t cols = src.cols();
    uint32_t rows = src.rows();
    uint32_t tilesX = params.divs;
    uint32_t tilesY = params.divs;

    uint32_t sizeX, sizeY, uiSubX, uiSubY; /* size of context. reg. and subimages */
    uint32_t uiXL, uiXR, uiYU, uiYB; /* auxiliary variables interpolation routine */

    uint16_t* pSrc; /* pointer to image */
    uint16_t* hist, *maps; /* pointer to histogram and mappings*/
    _maps.create(1, tilesX * tilesY * bins);
    _maps.clear();

    maps = _maps.first();

    sizeX = cols / tilesX;
    sizeY = rows / tilesY;
    uint32_t pixelsCount = sizeX * sizeY; /* Actual size of contextual regions */

    uint32_t clip = params.clipLimit * (sizeX * sizeY) / 100.0f;
    clip = Math::max(clip, 1u);

    uint32_t x, y; /* counters */

    /* Calculate greylevel mappings for each contextual region */
    for (y = 0, pSrc = pImage; y < tilesY; y++) {
        for (x = 0; x < tilesX; x++, pSrc += sizeX) {
            hist = &maps[bins * (y * tilesX + x)];
            makeHistogram(pSrc, cols, sizeX, sizeY, hist);
            clipHistogram(hist, bins, clip);
            mapHistogram(hist, max + 1, pixelsCount);
        }

        pSrc += (sizeY - 1) * cols; /* skip lines, set pointer */
    }

    auto pDst = dst.first();

    /* Interpolate greylevel mappings to get CLAHE image */
    for (y = 0, pSrc = pImage; y <= tilesY; y++) {
        if (y == 0) { /* special case: top row */
            uiSubY = sizeY >> 1;
            uiYU = 0;
            uiYB = 0;
        } else {
            if (y == tilesY) { /* special case: bottom row */
                uiSubY = sizeY >> 1;
                uiYU = tilesY - 1;
                uiYB = uiYU;
            } else { /* default values */
                uiSubY = sizeY;
                uiYU = y - 1;
                uiYB = uiYU + 1;
            }
        }

        for (x = 0; x <= tilesX; x++) {
            if (x == 0) { /* special case: left column */
                uiSubX = sizeX >> 1;
                uiXL = 0;
                uiXR = 0;
            } else {
                if (x == tilesX) { /* special case: right column */
                    uiSubX = sizeX >> 1;
                    uiXL = tilesX - 1;
                    uiXR = uiXL;
                } else { /* default values */
                    uiSubX = sizeX;
                    uiXL = x - 1;
                    uiXR = uiXL + 1;
                }
            }

            auto histLU = &maps[bins * (uiYU * tilesX + uiXL)];
            auto histRU = &maps[bins * (uiYU * tilesX + uiXR)];
            auto histLB = &maps[bins * (uiYB * tilesX + uiXL)];
            auto histRB = &maps[bins * (uiYB * tilesX + uiXR)];

            interpolateCompress(pSrc, cols, histLU, histRU, histLB, histRB, uiSubX, uiSubY, pDst);

            pDst += uiSubX;
            pSrc += uiSubX; /* set pointer on next matrix */
        }

        pSrc += (uiSubY - 1) * cols;
        pDst += (uiSubY - 1) * cols;
    }
}

void CLAHE::processPart(eye::Mat<int16_t> &, eye::Mat<uint8_t> &, bool ) {}

CLAHE::CLAHE(RangeScaler &scaler) : rangeScaler(scaler) {

}

bool CLAHE::onlyWholeFrame() {
    return true;
}

void CLAHE::setParams(std::vector<char> p) {
    memcpy(&params, p.data(), sizeof (Params));
}

std::vector<char> CLAHE::getParams() {
    return std::vector<char> {reinterpret_cast<char *>(&params), reinterpret_cast<char *>(&params + 1)};
}

CLAHE::~CLAHE() {

}

std::string CLAHE::name() {
    return "CLAHE";
}

void CLAHE::clipHistogram(uint16_t* hist, uint16_t bins, uint16_t clipLimit) {
    const auto end = &hist[bins];
    int32_t excess = 0;

    for (auto h = hist; h < end; h++) {
        int16_t binExcess = (int16_t)(*h - clipLimit);
        excess += binExcess > 0 ? binExcess : 0;
        *h = binExcess > 0 ? clipLimit : *h;
    }

    if (excess == 0) {
        return;
    }

    int32_t oldExcess = INT_MAX;

    /* Redistribute remaining excess  */
    while (excess > 0 && excess < oldExcess) {
        oldExcess = excess;
        uint32_t binInc = excess / bins; /* average binincrement */

        if (binInc > 0) {
            uint32_t upper = clipLimit - binInc;

            for (uint16_t* h = hist; h < end; h++) {
                if (*h >= clipLimit) {
                    *h = clipLimit;    /* clip bin */
                } else {
                    if (*h > upper) { /* high bin count */
                        excess -= clipLimit - *h;
                        *h = clipLimit;
                    } else { /* low bin count */
                        excess -= binInc;
                        *h += binInc;
                    }

                    if (excess <= 0) {
                        return;
                    }
                }
            }
        } else {
            for (uint16_t* h = hist; h < end; h++) {
                if (*h >= clipLimit) {
                    *h = clipLimit;    /* clip bin */
                } else {
                    excess--;
                    (*h)++;

                    if (excess == 0) {
                        return;
                    }
                }
            }
        }
    }
}

void CLAHE::makeHistogram(uint16_t* pImage, uint32_t cols, uint32_t sizeX, uint32_t sizeY, uint16_t* hist) {
    for (uint32_t i = 0; i < sizeY; i++) {
        auto pImagePointer = pImage + sizeX;

        while (pImage < pImagePointer) {
            hist[pImage[0]]++;
            hist[pImage[1]]++;
            hist[pImage[2]]++;
            hist[pImage[3]]++;
            hist[pImage[4]]++;
            hist[pImage[5]]++;
            hist[pImage[6]]++;
            hist[pImage[7]]++;
            pImage += 8;
        }

        pImage += cols - sizeX;
    }
}

void CLAHE::mapHistogram(uint16_t* hist, uint16_t range, uint32_t pixelsCount) {
    uint32_t sum = 0;
    uint32_t target_range, target_range_min, target_range_max;
    float fScale = 1.0f;

    rangeScaler.getTargetRangeMinMax(range, target_range, target_range_min, target_range_max);
    fScale = (float)(target_range - 1) / (pixelsCount - hist[0]);
    hist[0] = 0;

    for (auto h = hist; h < &hist[range]; h++) {
        sum += *h;
        *h = sum * fScale + 0.5f;
        *h += target_range_min;
    }
}

void CLAHE::interpolateCompress(uint16_t* pImage, uint32_t cols, uint16_t* histLU, uint16_t* histRU, uint16_t* histLB, uint16_t* histRB,
                                uint32_t xSize, uint32_t ySize, uint8_t* pDst) {
    const uint32_t stride = cols - xSize;
    uint32_t area = xSize * ySize;

    const uint32_t scale = (1 << 24) / (area);

    for (uint32_t y = 0, yInv = ySize; y < ySize; y++, yInv--, pImage += stride, pDst += stride) {
        for (uint32_t x = 0, xInv = xSize; x < xSize; x += 1, xInv -= 1) {

            uint32_t value = *pImage;

            uint32_t lu = histLU[value];
            uint32_t ru = histRU[value];
            uint32_t lb = histLB[value];
            uint32_t rb = histRB[value];

            uint32_t u = xInv * lu + x * ru;
            uint32_t b = xInv * lb + x * rb;

            uint32_t sum = (yInv * u + y * b);

            *pDst = static_cast<uint8_t>((sum * scale) >> 24);

            pImage += 1;
            pDst += 1;
        }
    }
}

