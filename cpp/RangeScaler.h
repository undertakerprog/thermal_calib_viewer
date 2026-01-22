#ifndef RANGESCALER_H
#define RANGESCALER_H

#include <cinttypes>
#include <cstring>
#include "IParams.h"

namespace eye {
namespace imgproc {

class RangeScaler : public IParams {
public:

    struct Params {
        uint32_t rangeScaleKeyPoint = 175;

        Params() = default;
        Params(const Params &) = default;
        Params(uint32_t s) : rangeScaleKeyPoint(s) {}
    } params;

    RangeScaler() = default;

    void setParams(std::vector<char> p) override {
        memcpy(&params, p.data(), sizeof (Params));
    }

    std::vector<char> getParams() override {
        return std::vector<char> {reinterpret_cast<char *>(&params), reinterpret_cast<char *>(&params + 1)};
    }

    void getTargetRangeMinMax(const uint32_t range, uint32_t &targetRange, uint32_t & targetRangeMin, uint32_t &targetRangeMax) {
        if (range < params.rangeScaleKeyPoint) {
            targetRange = range * 256 / params.rangeScaleKeyPoint;
        } else {
            targetRange = 256;
        }

        targetRangeMin  = (256 - targetRange) / 2;
        targetRangeMax  = targetRangeMin + targetRange - 1;
    }
};

}
}

#endif // RANGESCALER_H
