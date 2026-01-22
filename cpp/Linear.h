#ifndef LINEAR_COMPRESSOR_H
#define LINEAR_COMPRESSOR_H

#include "IParams.h"
#include "ImageProcessor.h"
#include "Histogram.h"

namespace eye {
namespace imgproc {

class Linear : public ImageProcessor, public IParams {

    Mat<uint8_t> map;
    Histogram& histogram;

    void MakeMap(int16_t min, int16_t max, int16_t avg);

public:
    Linear(Histogram& histogram);
    virtual ~Linear();
    virtual std::string name() override;
    virtual void process(eye::Mat<int16_t>& src, eye::Mat<uint8_t>& dst) override;
    virtual void processPart(eye::Mat<int16_t>& src, eye::Mat<uint8_t>& dst, bool isNewFrame) override;
    virtual bool onlyWholeFrame() override;
};

}  //namespace imgproc
}  //namespace eye

#endif // LINEAR_COMPRESSOR_H
