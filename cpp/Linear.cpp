#include "Linear.h"
#include "../core/mat_math.h"

namespace eye {
namespace imgproc {

void Linear::process(Mat<int16_t>& src, Mat<uint8_t>& dst) {
    int16_t min;
    int16_t avg;
    int16_t max;

    histogram.updateHistogram(src);
    histogram.getMinMaxAvgClipped(min, max, avg);
    MakeMap(min, max, avg);
    Math::mapImage(src, dst, map);
}

void Linear::processPart(eye::Mat<int16_t> &src, eye::Mat<uint8_t> &dst, bool isNewFrame) {
    histogram.updateHistogramPart(src, isNewFrame);

    if (isNewFrame) {
        int16_t min;
        int16_t avg;
        int16_t max;
        histogram.getMinMaxAvgClipped(min, max, avg);
        MakeMap(min, max, avg);
    }

    Math::mapImage(src, dst, map);
}

bool Linear::onlyWholeFrame() {
    return false;
}

Linear::Linear(Histogram& histogram) :
    histogram(histogram) {
    map.create(1, histogram.getHistogramSize());
}

Linear::~Linear() {

}

std::string Linear::name() {
    return "Linear";
}

void Linear::MakeMap(int16_t min, int16_t max, int16_t avg) {
    uint8_t * pMap = map.first();
    int mapSize    = map.size();

    int32_t rangeLo = avg - min + 1;
    int32_t rangeHi = max - avg;
    int32_t range   = rangeHi > rangeLo ? rangeHi : rangeLo;

    range = range == 0 ? 1 : range;

    int32_t targetRange = range > 128 ? 128 : range;
    float   scale       = float(targetRange) / float(range);

    memset(pMap, 0, size_t(avg));
    memset(pMap + avg, 255, size_t(map.total() - avg));

    int idx = avg;
    int i   = 0;

    while (1) {
        int val = int(128 - float(i) * scale);

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
        int val = int(128 + float(i) * scale);

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
