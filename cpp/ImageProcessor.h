#ifndef IMAGEPROCESSOR_H
#define IMAGEPROCESSOR_H

#include "../core/mat.h"

namespace eye {
namespace imgproc {

class ImageProcessor {
public:
    virtual ~ImageProcessor() {}
    virtual void process(eye::Mat<int16_t>& input, eye::Mat<uint8_t>& output) = 0;
    virtual void processPart(eye::Mat<int16_t>& src, eye::Mat<uint8_t>& dst, bool isNewFrame) = 0;
    virtual bool onlyWholeFrame() {
        return false;
    }
    virtual std::string name() = 0;
};

}
}

#endif // IMAGEPROCESSOR_H
