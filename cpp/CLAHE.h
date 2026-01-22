#ifndef CLAHE_H
#define CLAHE_H

#include "IParams.h"
#include "ImageProcessor.h"
#include "Histogram.h"
#include "RangeScaler.h"

namespace eye {
namespace imgproc {

class CLAHE : public ImageProcessor, public IParams {

    Mat<uint16_t> _maps;
    RangeScaler & rangeScaler;

    void clipHistogram(uint16_t* hist, uint16_t bins, uint16_t clipLimit);
    void makeHistogram(uint16_t* pImage, uint32_t cols, uint32_t sizeX, uint32_t sizeY, uint16_t* hist);
    void mapHistogram(uint16_t* hist, uint16_t range, uint32_t pixelsCount);
    void interpolateCompress(uint16_t* pImage, uint32_t uiXRes, uint16_t* pulMapLU, uint16_t* pulMapRU, uint16_t* pulMapLB, uint16_t* pulMapRB, uint32_t uiXSize, uint32_t uiYSize, uint8_t* pDst);

public:

    struct Params {
        int   divs = 4;
        float clipLimit = 1.0f;

        Params() = default;
        Params(int d, float cl) : divs(d), clipLimit(cl) {};
    } params;

    CLAHE(RangeScaler & scaler);
    virtual ~CLAHE();
    virtual std::string name() override;
    virtual void process(Mat<int16_t>& src, Mat<uint8_t>& dst) override;
    virtual void processPart(eye::Mat<int16_t>& src, eye::Mat<uint8_t>&dst, bool) override;
    virtual bool onlyWholeFrame() override;
    virtual void setParams(std::vector<char> p) override;
    virtual std::vector<char> getParams() override;
};

}
}

#endif // CLAHE_H
