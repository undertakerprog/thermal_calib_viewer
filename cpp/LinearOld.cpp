#include "LinearOld.h"
#include "../core/mat_math.h"

namespace eye {
namespace imgproc {

void LinearOld::process(Mat<int16_t>& src, Mat<uint8_t>& dst) {
    int16_t min, max, avg;
    histogram.updateHistogram(src);
    histogram.getMinMaxAvgClipped(min, max, avg);
    MakeMap(min, max, avg);
    Math::mapImage(src, dst, map);
}

void LinearOld::processPart(eye::Mat<int16_t> &src, eye::Mat<uint8_t> &dst, bool isNewFrame) {
    histogram.updateHistogramPart(src, isNewFrame);

    if (isNewFrame) {
        int16_t min, max, avg;
        histogram.getMinMaxAvgClipped(min, max, avg);
        MakeMap(min, max, avg);
    }

    Math::mapImage(src, dst, map);
}

bool LinearOld::onlyWholeFrame() {
    return false;
}

LinearOld::LinearOld(Histogram& histogram) :
    histogram(histogram) {
    map.create(1, histogram.getHistogramSize());
}

LinearOld::~LinearOld() {

}

std::string LinearOld::name() {
    return "Linear Old";
}

void LinearOld::MakeMap(int16_t min, int16_t max, int16_t avg) {
    uint8_t * pMap = map.first();

    int32_t range = max - min + 1;

    int32_t targetRange = range > 256 ? 256 : range;

    memset(pMap, 0, size_t(avg));
    memset(pMap + avg, 255, size_t(map.total() - avg));

    float scale = float(targetRange) / float(range);

    int idx = avg;
    int i = 0;

    while (1) {
        int val = int(128 - float(i) * scale);

        if (val < 0) {
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

        if (val > 255) {
            break;
        }

        pMap[idx] = uint8_t(val);

        ++i;
        ++idx;
    }
}

}
}
