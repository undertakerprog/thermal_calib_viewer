#include "Histogram.h"
#include "../core/math.h"

namespace eye {
namespace imgproc {

Histogram::Histogram() {
    hist1.create(1, histSize);
    hist2.create(1, histSize);
}

Histogram::~Histogram() {

}

void Histogram::setParams(std::vector<char> p) {
    memcpy(&params, p.data(), sizeof (Params));
}

std::vector<char> Histogram::getParams() {
    return std::vector<char> {reinterpret_cast<char *>(&params), reinterpret_cast<char *>(&params + 1)};
}

void Histogram::setFrameSize(uint32_t cols, uint32_t rows) {
    totalPixels = cols * rows;
}

void Histogram::updateHistogram(const eye::Mat<int16_t>& src) {
    accumHist->setTo(0);
    totalSum = 0;
    getHistAvg(src, *accumHist);
    avg = int16_t(double(totalSum) / src.total() + 0.5);
    std::swap(accumHist, readyHist);
    updateMinMaxClipped();
}

void Histogram::updateHistogramPart(const eye::Mat<int16_t> &src, bool isNewFrame) {
    if (isNewFrame) {
        avg = int16_t(double(totalSum) / totalPixels + 0.5);
        totalSum = 0;
        std::swap(accumHist, readyHist);
        updateMinMaxClipped();
        accumHist->setTo(0);
    }

    getHistAvg(src, *accumHist);
}

void Histogram::getMinMaxAvgClipped(int16_t &min, int16_t &max, int16_t &avg) {
    avg = this->avg;
    min = minClipped;
    max = maxClipped;

}

void Histogram::getMinMaxAvgReal(int16_t &min, int16_t &max, int16_t &avg) {
    min = this->min;
    max = this->max;
    avg = this->avg;
}

Mat<uint32_t> & Histogram::getHistogram() {
    return *readyHist;
}

uint32_t Histogram::getHistogramSize() {
    return histSize;
}

void Histogram::getHistAvg(const Mat<int16_t>& src, Mat<uint32_t>& hist) {
    uint32_t ms_sum[8] = {0};

    auto pHist = hist.first();
    auto ptr = src.first();
    auto end8 = src.first() + Math::alignLo(src.total(), 8);
    auto end1 = src.last();

    while (ptr < end8) {
        ++pHist[ptr[0]];
        ++pHist[ptr[1]];
        ++pHist[ptr[2]];
        ++pHist[ptr[3]];
        ++pHist[ptr[4]];
        ++pHist[ptr[5]];
        ++pHist[ptr[6]];
        ++pHist[ptr[7]];

        ms_sum[0] += ptr[0];
        ms_sum[1] += ptr[1];
        ms_sum[2] += ptr[2];
        ms_sum[3] += ptr[3];
        ms_sum[4] += ptr[4];
        ms_sum[5] += ptr[5];
        ms_sum[6] += ptr[6];
        ms_sum[7] += ptr[7];

        ptr += 8;
    }

    while (ptr < end1) {
        ++pHist[*ptr];
        totalSum += *ptr;
        ++ptr;
    }

    totalSum += ms_sum[0];
    totalSum += ms_sum[1];
    totalSum += ms_sum[2];
    totalSum += ms_sum[3];
    totalSum += ms_sum[4];
    totalSum += ms_sum[5];
    totalSum += ms_sum[6];
    totalSum += ms_sum[7];
}

void Histogram::updateMinMaxClipped() {

    auto pHist = readyHist->first();
    auto pEnd  = readyHist->last();

    while (*pHist == 0 && pHist != pEnd) {
        ++pHist;
    }

    if (pHist == pEnd) {
        minClipped = min = 0;
        maxClipped = max = 0;
        return;
    }

    min = pHist - readyHist->first();
    uint32_t skipped = *pHist;

    while (skipped < params.clipLo) {
        skipped += *pHist;
        ++pHist;
    }

    minClipped = pHist - readyHist->first();
    pHist = readyHist->last() - 1;

    while (*pHist == 0) {
        --pHist;
    }

    max = pHist - readyHist->first();
    skipped = *pHist;

    while (skipped < params.clipHi) {
        skipped += *pHist;
        --pHist;
    }

    maxClipped = pHist - readyHist->first();
}

}
}
