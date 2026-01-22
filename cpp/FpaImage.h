#pragma once
#include "mat.h"

#include <istream>
#include <ostream>
#include <iostream>

namespace eye {
template<class T>
class FpaImage : public Mat<T> {
public:
    float tAdc = 0.0f;

    FpaImage() {}

    FpaImage(FpaImage && mat) {
        tAdc = mat.tAdc;
        Mat<T>::operator=(std::move(mat));
    }

    FpaImage<T>& operator=(FpaImage<T>&& mat) {
        tAdc = mat.tAdc;
        Mat<T>::operator=(std::move(mat));
        return *this;
    }

    FpaImage(const FpaImage & mat) {
        tAdc = mat.tAdc;
        Mat<T>::operator=(mat);
    }

    FpaImage<T>& operator=(const FpaImage<T>& mat) {
        tAdc = mat.tAdc;
        Mat<T>::operator=(mat);
        return *this;
    }

    FpaImage(int rows, int cols, int channels = 1) : Mat<T>(rows, cols, channels) {}

    FpaImage(int rows, int cols, int channels, void* data) : Mat<T>(rows, cols, channels, data) {}

    virtual bool save(std::ostream& os) override {
        os.write((char*)&tAdc, sizeof(tAdc));
        Mat<T>::save(os);
        return true;
    }

    virtual bool load(std::istream& is) override {
        is.read((char*)&tAdc, sizeof(tAdc));
        Mat<T>::load(is);
        return true;
    }

    virtual bool save(const std::string& path) override {
        std::ofstream ofs(path.c_str(), std::ofstream::binary);

        if (!ofs) {
            return false;
        }

        return save(ofs);
    }

    virtual bool load(const std::string& path) override {
        std::ifstream ifs(path, std::ofstream::binary);

        if (!ifs) {
            return false;
        }

        return load(ifs);
    }
};

template <typename T>
bool operator <(const FpaImage<T>& a, const FpaImage<T>& b) {
    return a.tAdc < b.tAdc;
}
}
