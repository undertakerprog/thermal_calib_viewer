#include "LHE.h"
#include "../core/mat_math.h"

namespace eye {
namespace imgproc {

LHE::LHE(Histogram &histogram, RangeScaler &scaler) :
    histogram(histogram), rangeScaler(scaler) {
    map.create(1, histogram.getHistogramSize());
}

void LHE::process(Mat<int16_t> &src, Mat<uint8_t> &dst) {
    histogram.updateHistogram(src);
    histogram.getMinMaxAvgClipped(minClipped, maxClipped, avg);

    auto & hist = histogram.getHistogram();

    clipHistogram(hist, params.clipLimit);
    MakeMap(map, hist);
    Math::mapImage(src, dst, map);
}

void LHE::processPart(eye::Mat<int16_t> &src, eye::Mat<uint8_t> &dst, bool isNewFrame) {
    histogram.updateHistogramPart(src, isNewFrame);

    if (isNewFrame) {
        histogram.getMinMaxAvgClipped(minClipped, maxClipped, avg);
        auto & hist = histogram.getHistogram();
        clipHistogram(hist, params.clipLimit);
        MakeMap(map, hist);
    }

    Math::mapImage(src, dst, map);
}

bool LHE::onlyWholeFrame() {
    return false;
}

void LHE::setParams(std::vector<char> p) {
    memcpy(&params, p.data(), sizeof (Params));
}

std::vector<char> LHE::getParams() {
    return std::vector<char> {reinterpret_cast<char *>(&params), reinterpret_cast<char *>(&params + 1)};
}

LHE::~LHE() {}

std::string LHE::name() {
    return "LHE";
}

void LHE::clipHistogram(Mat<uint32_t>& hist, uint32_t threshold) {
    uint32_t * pHist = hist.first() + minClipped;
    uint32_t * pEnd  = hist.first() + maxClipped + 1;

    totalClipped = 0;

    while (pHist < pEnd) {
        uint32_t value = *pHist > threshold ? threshold : *pHist;
        *pHist = value;
        totalClipped += value;
        ++pHist;
    }
}

void LHE::MakeMap(Mat<uint8_t>& map, Mat<uint32_t>& hist) {
    uint8_t  * pMap    = map.first() + minClipped;
    uint8_t  * pMapEnd = map.first() + maxClipped + 1;
    uint32_t * pHist  = hist.first() + minClipped;

    uint64_t sum = 0;
    uint32_t range = maxClipped - minClipped + 1;
    uint32_t targetRange, targetRangeMin, targetRangeMax;

    rangeScaler.getTargetRangeMinMax(range, targetRange, targetRangeMin, targetRangeMax);
    float scale = (float)(targetRange - 1) / totalClipped;

    memset(map.first(), 0, minClipped);
    memset(map.first() + maxClipped, 255, map.total() - maxClipped);

    while (pMap < pMapEnd) {
        sum += *pHist;
        *pMap = sum * scale + targetRangeMin;
        ++pHist;
        ++pMap;
    }

    scale = float(targetRange) / range;
    pMap = map.first();

    int idx = minClipped - 1;
    int i = 0;

    while (1) {
        int val = int(targetRangeMin - float(i++) * scale);

        if (val < 0 || idx < 0) {
            break;
        }

        pMap[idx--] = uint8_t(val);
    }

    idx = maxClipped + 1;
    i = 0;

    int mapSize = map.size();

    while (1) {
        int val = int(targetRangeMax + float(i++) * scale);

        if (val > 255 || idx >= mapSize) {
            break;
        }

        pMap[idx++] = uint8_t(val);
    }
}

}
}

