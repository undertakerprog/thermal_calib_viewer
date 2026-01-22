#ifndef LINEARFULLSCALE_H
#define LINEARFULLSCALE_H

#include "IParams.h"
#include "ImageProcessor.h"
#include "Histogram.h"
#include "RangeScaler.h"

namespace eye {
namespace imgproc {

class LinearFullScale : public ImageProcessor, public IParams {

    Mat<uint8_t> map;
    Histogram & histogram;
    RangeScaler & rangeScaler;

    void MakeMap(int16_t min, int16_t max, int16_t avg);

public:
    LinearFullScale(Histogram & histogram, RangeScaler & scaler);
    virtual ~LinearFullScale();
    virtual std::string name() override;
    virtual void process(Mat<int16_t>& src, Mat<uint8_t>& dst) override;
    virtual void processPart(eye::Mat<int16_t> &src, eye::Mat<uint8_t> &dst, bool isNewFrame) override;
    virtual bool onlyWholeFrame() override;
};

}  // namespace imgproc
}  // namespace eye

#endif // LINEARFULLSCALE_H
