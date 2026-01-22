#include "ImageProcessorsManager.h"
#include "../DataStructures.h"
#include <vector>

namespace eye {
namespace imgproc {

ImageProcessorsManager::ImageProcessorsManager() {
    processors[Algorithm::Linear] = new Linear(histogram);
    processors[Algorithm::CLAHE]  = new CLAHE(rangeScaler);
    processors[Algorithm::LinearFullScale] = new LinearFullScale(histogram, rangeScaler);
    processors[Algorithm::PowLogHE] = new PowLogHE(histogram, rangeScaler);
    processors[Algorithm::LinearDoubleScale] = new LinearDoubleScale(histogram);
    processors[Algorithm::LinearOld] = new LinearOld(histogram);
    processors[Algorithm::LHE] = new LHE(histogram, rangeScaler);

    currentProcessor = pendingProcessor = Algorithm::Linear;

    unitsWithParams[Algorithm::Histogram] = &histogram;
    unitsWithParams[Algorithm::RangeScaler] = &rangeScaler;

    for (auto & p : processors) {
        unitsWithParams[p.first] = dynamic_cast<IParams *>(p.second);
    }

    filters[Algorithm::LinearNoiseReductor] = new LinearNoiseReductor;
    filters[Algorithm::LinearLaplace3x1] = new LinearLaplace3x1;
    filters[Algorithm::LinearLaplace5x1] = new LinearLaplace5x1;
    filters[Algorithm::LinearLaplacePure3x1] = new LinearLaplacePure3x1;
    filters[Algorithm::LinearLaplacePure5x1] = new LinearLaplacePure5x1;
    filters[Algorithm::LinearSobel3x1] = new LinearSobel3x1;
    filters[Algorithm::LinearSobelPure3x1] = new LinearSobelPure3x1;
    filters[Algorithm::LinearRoberts2x1] = new LinearRoberts2x1;
    filters[Algorithm::LinearRobertsPure2x1] = new LinearRobertsPure2x1;

    currentFilter = pendingFilter = Algorithm::None;

    sendData = [](size_t, void *) {};
}

ImageProcessorsManager::~ImageProcessorsManager() {

}

void ImageProcessorsManager::setAlgo(Algorithm alg) {
    if (processors.find(alg) != processors.end()) {
        pendingProcessor = alg;
    }
}

ImageProcessor * ImageProcessorsManager::getProc(Algorithm alg) {
    if (processors.find(alg) != processors.end()) {
        return processors.at(alg);
    }

    return nullptr;
}

ImageProcessor * ImageProcessorsManager::getCurrentProcessor() {
    return processors.at(currentProcessor);
}

Histogram& ImageProcessorsManager::getHistogram() {
    return histogram;
}

std::string ImageProcessorsManager::getListProcessors() {
    std::string list;

    for (auto iter = processors.begin(); iter != processors.end(); ++iter) {
        list += std::to_string(static_cast<int>(iter->first));
        list += ":";
        list += iter->second->name();
        list += ";";
    }

    list.pop_back();
    return list;
}

void ImageProcessorsManager::setFilter(Algorithm filter) {
    if (filter == Algorithm::None || filters.find(filter) != filters.end()) {
        pendingFilter = filter;
    }
}

void ImageProcessorsManager::setFrameSize(uint32_t cols, uint32_t rows) {
    histogram.setFrameSize(cols, rows);
}

void ImageProcessorsManager::processParams(void *params, size_t paramsLength) {
    if (params == nullptr || paramsLength == 0) {
        return;
    }

    using MT  = ImageProcessingParams::MessageType;
    using AN  = ImageProcessingParams::AlgorithmName;
    using LAP = ImageProcessingParams::ListAlgorithmsParams;

    ImageProcessingParams * recvParams = reinterpret_cast<ImageProcessingParams *>(params);

    switch (recvParams->getType()) {
    case MT::GetListAlgorithms : {
        ImageProcessingParams reply(MT::GetListAlgorithms);
        reply.listAlgorithmsParams = LAP(static_cast<uint32_t>(currentProcessor), sizeof (ImageProcessingParams), processors.size());

        std::vector<uint8_t> buffer(reinterpret_cast<uint8_t *>(&reply), reinterpret_cast<uint8_t *>(&reply + 1));

        for (auto & p : processors) {
            AN alg(static_cast<uint32_t>(p.first), p.second->name());
            std::copy(reinterpret_cast<uint8_t *>(&alg), reinterpret_cast<uint8_t *>(&alg + 1), std::back_inserter(buffer));
        }

        sendData(buffer.size(), buffer.data());
    }
    break;

    case MT::SetAlgorithm : {
        setAlgo(static_cast<Algorithm>(recvParams->algorithmId));
    }
    break;

    case MT::GetListFilters: {
        ImageProcessingParams reply(MT::GetListFilters);
        reply.listAlgorithmsParams = LAP(static_cast<uint32_t>(currentFilter), sizeof (ImageProcessingParams), filters.size());

        std::vector<uint8_t> buffer(reinterpret_cast<uint8_t *>(&reply), reinterpret_cast<uint8_t *>(&reply + 1));

        AN alg(static_cast<uint32_t>(Algorithm::None), "None");
        std::copy(reinterpret_cast<uint8_t *>(&alg), reinterpret_cast<uint8_t *>(&alg + 1), std::back_inserter(buffer));

        for (auto & p : filters) {
            AN alg(static_cast<uint32_t>(p.first), p.second->name());
            std::copy(reinterpret_cast<uint8_t *>(&alg), reinterpret_cast<uint8_t *>(&alg + 1), std::back_inserter(buffer));
        }

        sendData(buffer.size(), buffer.data());
    }
    break;

    case MT::SetFilter : {
        setFilter(static_cast<Algorithm>(recvParams->algorithmId));
    }
    break;

    case MT::GetParams : {
        using PH = ImageProcessingParams::ParamsHeader;

        ImageProcessingParams reply(MT::SetParams);
        reply.paramsOffset = sizeof (ImageProcessingParams);

        std::vector<uint8_t> buffer(reinterpret_cast<uint8_t *>(&reply), reinterpret_cast<uint8_t *>(&reply + 1));

        for (auto & p : unitsWithParams) {
            auto unitParams = p.second->getParams();

            if (!unitParams.empty()) {
                PH header(static_cast<uint32_t>(p.first), unitParams.size());
                std::copy(reinterpret_cast<uint8_t *>(&header), reinterpret_cast<uint8_t *>(&header + 1), std::back_inserter(buffer));
                std::copy(unitParams.begin(), unitParams.end(), std::back_inserter(buffer));
            }
        }

        sendData(buffer.size(), buffer.data());
    }
    break;

    case MT::SetParams : {
        using PH = ImageProcessingParams::ParamsHeader;

        PH * pHeader = reinterpret_cast<PH *>(reinterpret_cast<char *>(recvParams) + recvParams->paramsOffset);
        PH * pHeaderEnd = reinterpret_cast<PH *>(reinterpret_cast<char *>(recvParams) + paramsLength);

        while (pHeader < pHeaderEnd) {
            auto iter = unitsWithParams.find(static_cast<Algorithm>(pHeader->id));

            char * ptr = reinterpret_cast<char *>(pHeader + 1);
            char * ptrEnd = ptr + pHeader->size;

            if (iter != unitsWithParams.end()) {
                iter->second->setParams({ptr, ptrEnd});
            }

            pHeader = reinterpret_cast<PH *>(reinterpret_cast<char *>(pHeader + 1) + pHeader->size);
        }
    }
    break;

    default:
        return;
    }
}

void ImageProcessorsManager::process(Mat<int16_t>& src, Mat<uint8_t>& dst) {
    currentProcessor = pendingProcessor;
    currentFilter    = pendingFilter;

    if (currentFilter != Algorithm::None) {
        filters.at(currentFilter)->applyFilter(src, src);
    }

    processors.at(currentProcessor)->process(src, dst);
}

void ImageProcessorsManager::processPart(Mat<int16_t> &src, Mat<uint8_t> &dst, bool isFirstPart, bool isLastPart) {
    if (currentFilter != Algorithm::None) {
        filters.at(currentFilter)->applyFilter(src, src);
    }

    processors.at(currentProcessor)->processPart(src, dst, isFirstPart);

    if (isLastPart) {
        currentProcessor = pendingProcessor;
        currentFilter    = pendingFilter;
    }
}

}
}
