#include "LinearDoubleScale.h"
#include "../core/mat_math.h"

namespace eye {
namespace imgproc {

LinearDoubleScale::LinearDoubleScale(Histogram &histogram) :
    histogram(histogram) {
    map.create(1, histogram.getHistogramSize());
}

LinearDoubleScale::~LinearDoubleScale() {

}

std::string LinearDoubleScale::name() {
    return "Linear DS";
}

void LinearDoubleScale::process(Mat<int16_t>& src, Mat<uint8_t>& dst) {
    int16_t min, max, avg;
    histogram.updateHistogram(src);
    histogram.getMinMaxAvgClipped(min, max, avg);
    MakeMap(min, max, avg);
    Math::mapImage(src, dst, map);
}

void LinearDoubleScale::processPart(eye::Mat<int16_t> &src, eye::Mat<uint8_t> &dst, bool isNewFrame) {
    histogram.updateHistogramPart(src, isNewFrame);

    if (isNewFrame) {
        int16_t min, max, avg;
        histogram.getMinMaxAvgClipped(min, max, avg);
        MakeMap(min, max, avg);
    }

    Math::mapImage(src, dst, map);
}

bool LinearDoubleScale::onlyWholeFrame() {
    return false;
}

void LinearDoubleScale::MakeMap(int16_t min, int16_t max, int16_t avg) {
    uint8_t * pMap = map.first();
    int mapSize    = map.size();

    int32_t rangeLo = avg - min + 1;
    int32_t rangeHi = max - avg;

    rangeLo = rangeLo == 0 ? 1 : rangeLo;
    rangeHi = rangeHi == 0 ? 1 : rangeHi;

    int32_t targetRangeLo = rangeLo > 128 ? 128 : rangeLo;
    int32_t targetRangeHi = rangeHi > 128 ? 128 : rangeHi;

    memset(pMap, 0, size_t(avg));
    memset(pMap + avg, 255, size_t(map.total() - avg));

    float scaleLo = float(targetRangeLo) / float(rangeLo);
    float scaleHi = float(targetRangeHi) / float(rangeHi);

    int idx = avg;
    int i = 0;

    while (1) {
        int val = int(128 - float(i) * scaleLo);

        if (val < 0 || idx < 0) {
            break;
        }

        pMap[idx] = uint8_t(val);

        ++i;
        --idx;
    }

    idx = avg + 1;
    i = 1;

    while (1) {
        int val = int(128 + float(i) * scaleHi);

        if (val > 255 || idx >= mapSize) {
            break;
        }

        pMap[idx] = uint8_t(val);

        ++i;
        ++idx;
    }
}

}
}
