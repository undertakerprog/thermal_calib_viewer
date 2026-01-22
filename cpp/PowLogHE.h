#ifndef POWLOGHE_H
#define POWLOGHE_H

#include "IParams.h"
#include "ImageProcessor.h"
#include "Histogram.h"
#include "RangeScaler.h"

namespace eye {
namespace imgproc {

class PowLogHE : public ImageProcessor, public IParams {

    int16_t  avg;
    int16_t  minClipped;
    int16_t  maxClipped;
    uint32_t totalClipped;

    Mat<uint8_t> map;

    Histogram & histogram;
    RangeScaler & rangeScaler;

    void TransformHistogram(Mat<uint32_t> &hist);
    void ClipHistogram(Mat<uint32_t> &hist);
    void MakeMap(Mat<uint8_t>& map, Mat<uint32_t>& hist);

public:

    struct Params {
        uint32_t threshold = 100;
        uint32_t additive = 16;
        float    exponent = 2.0f;

        Params() = default;
        Params(uint32_t thr, uint32_t a, float e) : threshold(thr), additive(a), exponent(e) {}
    } params;

    PowLogHE(Histogram & histogram, RangeScaler &scaler);
    virtual ~PowLogHE();
    virtual std::string name() override;
    virtual void process(Mat<int16_t> & input_image, Mat<uint8_t> & dst) override;
    virtual void processPart(eye::Mat<int16_t>& src, eye::Mat<uint8_t>& dst, bool isNewFrame = true) override;
    virtual bool onlyWholeFrame() override;
    virtual void setParams(std::vector<char> p) override;
    virtual std::vector<char> getParams() override;
};

}
}
#endif // POWLOGHE
