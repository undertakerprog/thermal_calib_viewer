#ifndef LHE_H
#define LHE_H

#include "IParams.h"
#include "ImageProcessor.h"
#include "Histogram.h"
#include "RangeScaler.h"

namespace eye {
namespace imgproc {

class LHE : public ImageProcessor, public IParams {
    int16_t avg;
    int16_t minClipped;
    int16_t maxClipped;
    uint32_t totalClipped;

    Mat<uint8_t> map;

    Histogram & histogram;
    RangeScaler & rangeScaler;

    void clipHistogram(Mat<uint32_t>& hist, uint32_t threshold);
    void MakeMap(Mat<uint8_t>& map, Mat<uint32_t>& hist);

public:

    struct Params {
        uint32_t clipLimit = 100;

        Params() = default;
        Params(uint32_t cl) : clipLimit(cl) {}
    } params;

    LHE(Histogram & histogram, RangeScaler & scaler);
    virtual ~LHE();
    virtual std::string name() override;
    virtual void process(Mat<int16_t> & input_image, Mat<uint8_t> & dst) override;
    virtual void processPart(eye::Mat<int16_t>& src, eye::Mat<uint8_t>& dst, bool isNewFrame = true) override;
    virtual bool onlyWholeFrame() override;
    virtual void setParams(std::vector<char> p) override;
    virtual std::vector<char> getParams() override;
};

}
}

#endif // LHE_H
