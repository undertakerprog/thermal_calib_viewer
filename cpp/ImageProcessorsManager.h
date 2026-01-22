#ifndef IMAGEPROCESSORSMANAGER_H
#define IMAGEPROCESSORSMANAGER_H

#include <string>
#include <unordered_map>
#include <functional>

#include "Histogram.h"
#include "RangeScaler.h"
#include "ImageProcessor.h"
#include "filters/IFilter.h"

#include "Linear.h"
#include "LinearFullScale.h"
#include "CLAHE.h"
#include "PowLogHE.h"
#include "LinearDoubleScale.h"
#include "LinearOld.h"
#include "LHE.h"

#include "filters/IFilter.h"
#include "filters/LinearNoiseReductor.h"
#include "filters/LinearLaplace3x1.h"
#include "filters/LinearLaplace5x1.h"
#include "filters/LinearLaplacePure3x1.h"
#include "filters/LinearLaplacePure5x1.h"
#include "filters/LinearRoberts2x1.h"
#include "filters/LinearRobertsPure2x1.h"
#include "filters/LinearSobel3x1.h"
#include "filters/LinearSobelPure3x1.h"

namespace eye {
namespace imgproc {

enum class Algorithm {
    PowLogHE = 0,
    CLAHE,
    Linear,
    LinearFullScale = 4,
    Test = 12,
    LinearDoubleScale,
    LinearOld,
    LHE,

    Histogram = 50,
    RangeScaler,

    LinearNoiseReductor = 100,
    LinearLaplace3x1 = 120,
    LinearLaplace5x1,
    LinearLaplacePure3x1 = 130,
    LinearLaplacePure5x1,
    LinearSobel3x1 = 140,
    LinearSobelPure3x1 = 150,
    LinearRoberts2x1 = 160,
    LinearRobertsPure2x1 = 170,

    None = 1000
};

class ImageProcessorsManager {

    std::unordered_map<Algorithm, ImageProcessor *> processors;
    std::unordered_map<Algorithm, IFilter *> filters;
    std::unordered_map<Algorithm, IParams *> unitsWithParams;

    Histogram histogram;
    RangeScaler rangeScaler;

    Algorithm currentProcessor = Algorithm::PowLogHE;
    Algorithm pendingProcessor = Algorithm::PowLogHE;
    Algorithm currentFilter = Algorithm::None;
    Algorithm pendingFilter = Algorithm::None;

public:
    ImageProcessorsManager();
    ~ImageProcessorsManager();

    std::function<void(size_t size, void * buf)> sendData;

    void            setAlgo(Algorithm alg);
    ImageProcessor* getProc(Algorithm alg);
    ImageProcessor* getCurrentProcessor();
    Histogram&      getHistogram();
    std::string     getListProcessors();

    void setFilter(Algorithm filter);

    void setFrameSize(uint32_t cols, uint32_t rows);
    void processParams(void * params, size_t paramsLength);

    void process(Mat<int16_t>& src, Mat<uint8_t>& dst);
    void processPart(Mat<int16_t>& src, Mat<uint8_t>& dst, bool isFirstPart, bool isLastPart);
};

}
}
#endif // IMAGEPROCESSORSMANAGER_H
