#ifndef HISTOGRAM_H
#define HISTOGRAM_H

#include "../core/mat.h"
#include "IParams.h"
#include <limits>

namespace eye {
namespace imgproc {

class Histogram : public IParams {

    uint32_t histSize = std::numeric_limits<int16_t>().max() * 1.5;
    uint32_t totalPixels = 640 * 480;
    uint64_t totalSum = 0;

    int16_t min;
    int16_t max;
    int16_t avg;
    int16_t minClipped;
    int16_t maxClipped;

    Mat<uint32_t> hist1;
    Mat<uint32_t> hist2;

    Mat<uint32_t> * readyHist = &hist1;
    Mat<uint32_t> * accumHist = &hist2;

    void getHistAvg(const Mat<int16_t>& src, Mat<uint32_t>& hist);
    void updateMinMaxClipped();

public:

    struct Params {
        uint32_t clipLo = 100;
        uint32_t clipHi = 100;

        Params() = default;
        Params(uint32_t cl, uint32_t ch) : clipLo(cl), clipHi(ch) {}
    } params;

    Histogram();
    ~Histogram();

    void setParams(std::vector<char> params) override;
    std::vector<char> getParams() override;

    void setFrameSize(uint32_t cols, uint32_t rows);
    void updateHistogram(const eye::Mat<int16_t> & src);
    void updateHistogramPart(const eye::Mat<int16_t> &src, bool isNewFrame = true);
    void getMinMaxAvgClipped(int16_t & min, int16_t & max, int16_t & avg);
    void getMinMaxAvgReal(int16_t &min, int16_t &max, int16_t &avg);
    Mat<uint32_t> &getHistogram();
    uint32_t getHistogramSize();
};

}
}
#endif // HISTOGRAM_H
