#include "LinearFullScale.h"
#include "../core/mat_math.h"

namespace eye {
namespace imgproc {

LinearFullScale::LinearFullScale(Histogram &histogram, RangeScaler &scaler) :
    histogram(histogram), rangeScaler(scaler) {
    map.create(1, histogram.getHistogramSize());
}

LinearFullScale::~LinearFullScale() {

}

std::string LinearFullScale::name() {
    return "Linear FS";
}

void LinearFullScale::process(Mat<int16_t>& src, Mat<uint8_t>& dst) {
    int16_t min, max, avg;
    histogram.updateHistogram(src);
    histogram.getMinMaxAvgClipped(min, max, avg);
    MakeMap(min, max, avg);
    Math::mapImage(src, dst, map);
}

void LinearFullScale::processPart(eye::Mat<int16_t> &src, eye::Mat<uint8_t> &dst, bool isNewFrame) {
    histogram.updateHistogramPart(src, isNewFrame);

    if (isNewFrame) {
        int16_t min, max, avg;
        histogram.getMinMaxAvgClipped(min, max, avg);
        MakeMap(min, max, avg);
    }

    Math::mapImage(src, dst, map);
}

bool LinearFullScale::onlyWholeFrame() {
    return false;
}

void LinearFullScale::MakeMap(int16_t min, int16_t max, int16_t avg) {
    uint8_t * pMap = map.first();
    uint32_t range = max - min + 1;
    uint32_t targetRange, targetRangeMin, targetRangeMax;
    float scale;

    rangeScaler.getTargetRangeMinMax(range, targetRange, targetRangeMin, targetRangeMax);
    scale = (float)(targetRange - 1) / (range - 1);

    memset(pMap, 0, avg);
    memset(pMap + avg, 255, map.total() - avg);

    int idx = min;
    int i = 0;

    while (1) {
        int val = int(targetRangeMin - float(i++) * scale);

        if (val < 0 || idx < 0) {
            break;
        }

        pMap[idx--] = uint8_t(val);
    }

    idx = min + 1;
    i = 1;

    int mapSize = map.size();

    while (1) {
        int val = int(targetRangeMin + float(i++) * scale);

        if (val > 255 || idx >= mapSize) {
            break;
        }

        pMap[idx++] = uint8_t(val);
    }
}

}
}
