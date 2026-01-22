#pragma once

#include <fstream>
#include <memory>
#include <string.h>
#include <utility>

#include "rect.h"

namespace eye {
template <typename T>
class Mat {
protected:
    bool _isMemoryOwner = false;
    int _cols = 0;
    int _rows = 0;
    int _channels = 1;
    uint64_t _allocated = 0;
    T* _first = nullptr;
    T* _last = nullptr;

    void init() {
        if (_isMemoryOwner) {
            release();
            _allocated = size();
            _first = (T*)malloc(_allocated);
        }

        _last = _first + size() / sizeof(T);
    }

public:
    Mat() {}

    Mat(Mat&& mat) {
        this->_isMemoryOwner = mat._isMemoryOwner;
        this->_cols = mat._cols;
        this->_rows = mat._rows;
        this->_channels = mat._channels;
        this->_allocated = mat._allocated;
        this->_first = mat._first;
        this->_last = mat._last;

        mat._isMemoryOwner = false;
        mat.release();
    }

    Mat& operator= (Mat&& mat) {
        this->release();
        this->_isMemoryOwner = mat._isMemoryOwner;
        this->_cols = mat._cols;
        this->_rows = mat._rows;
        this->_channels = mat._channels;
        this->_allocated = mat._allocated;
        this->_first = mat._first;
        this->_last = mat._last;
        mat._isMemoryOwner = false;
        mat.release();
        return *this;
    }

    Mat(const Mat<T>& mat) {
        this->_isMemoryOwner = true;
        this->_cols = mat._cols;
        this->_rows = mat._rows;
        this->_channels = mat._channels;
        init();
        memcpy(_first, mat.first(), _allocated);
    }

    Mat& operator=(const Mat& mat) {
        this->release();
        this->_isMemoryOwner = true;
        this->_cols = mat._cols;
        this->_rows = mat._rows;
        this->_channels = mat._channels;
        init();
        memcpy(_first, mat.first(), _allocated);
        return *this;
    }

    Mat(int rows, int cols, int channels = 1)
        : _isMemoryOwner(true)
        , _cols(cols)
        , _rows(rows)
        , _channels(channels) {
        init();
    }

    Mat(int rows, int cols, int channels, void* data)
        : _isMemoryOwner(false)
        , _cols(cols)
        , _rows(rows)
        , _channels(channels)
        , _first((T*)data) {
        init();
    }

    virtual ~Mat() {
        release();
    }

    void release() {
        if (_isMemoryOwner && _first != nullptr) {
            free(_first);
            _allocated = 0;
        }

        _first = nullptr;
        _last = nullptr;
    }

    static std::shared_ptr<Mat<T> > make(int rows, int cols, int channels = 1) {
        return std::make_shared<Mat<T> >(rows, cols, channels);
    }

    static std::shared_ptr<Mat<T> > make(int rows, int cols, int channels, void* data) {
        return std::make_shared<Mat<T> >(rows, cols, channels, data);
    }

    Rect roi() {
        return Rect(0, 0, _cols, _rows);
    }

    int cols() const {
        return _cols;
    }

    int rows() const {
        return _rows;
    }

    int channels() const {
        return _channels;
    }

    int pixSize() const {
        return sizeof(T) * _channels;
    }

    int bpp() const {
        return pixSize() * 8;
    }

    int step() const {
        return sizeof(T);
    }

    int stride() const {
        return _cols * pixSize();
    }

    int total() const {
        return _cols * _rows;
    }

    size_t size() const {
        return stride() * _rows;
    }

    int cvDepth() const;

    int type() const {
        return 3;
    }

    uint8_t* beg() const {
        return (uint8_t*)_first;
    }

    uint8_t* end() const {
        return (uint8_t*)_last;
    }

    T* first() const {
        return _first;
    }

    T* last() const {
        return _last;
    }

    T* at(int index) const {
        return _first + index * _channels;
    }
    T* at(int y, int x) const {
        return _first + (y * _cols + x ) * _channels;
    }

    bool exist() const {
        return _first != nullptr;
    }

    bool isSameSize(int rows, int cols, int channels) const {
        return _first != nullptr && _rows == rows && _cols == cols && _channels == channels;
    }

    template <typename TOther>
    bool isSameSize(const Mat<TOther>& other) const {
        return isSameSize(other.rows(), other.cols(), other.channels());
    }

    bool haveSpace(int rows, int cols, int channels) const {
        return _first != nullptr && _allocated >= rows * cols * channels * sizeof(T);
    }

    void* ptr(int position) const {
        return (void*)(_first + position * _channels);
    }

    bool create(int rows, int cols, int channels = 1) {
        if (isSameSize(rows, cols, channels)) {
            return false;
        }

        if (haveSpace(rows, cols, channels)) {
            _rows = rows;
            _cols = cols;
            _channels = channels;
            _last = _first + rows * cols * channels;
            return false;
        }

        if (_first != nullptr && !_isMemoryOwner) {
            return false;
        }

        _isMemoryOwner = true;
        _rows = rows;
        _cols = cols;
        _channels = channels;
        init();

        return true;
    }

    bool create(const Mat<T>& reference) {
        return create(reference.rows(), reference.cols(), reference.channels());
    }

    template <typename TOther>
    bool create(const Mat<TOther>& reference) {
        return create(reference.rows(), reference.cols(), reference.channels());
    }

    void copyTo(Mat<T>& other) const {
        other.create(*this);
        memcpy(other.beg(), beg(), size());
    }

    void setTo(T value) {
        auto cur = _first;

        while (cur < _last) {
            *cur = value;
            ++cur;
        }
    }

    void setTo(T value, const Rect& roi) {
        auto tl = roi.tl();
        auto br = roi.br();

        for (int y = tl.y; y < br.y; y++) {
            auto ptr = _first + (_cols * y + tl.x) * _channels;
            auto end = ptr + roi.width * _channels;

            while (ptr < end) {
                *ptr = value;
                ++ptr;
            }
        }
    }

    void clear() const {
        if (_first == nullptr) {
            return;
        }

        memset(beg(), 0, size());
    }

    Mat<T> operator()(const Rect& roi) {
        Mat<T> mat;
        mat.create(roi.height, roi.width, _channels);

        int x0 = roi.x;
        int y0 = roi.y;
        int y1 = roi.y + roi.height;

        size_t n = roi.width * sizeof(T) * _channels;

        for (int i = y0, j = 0; i < y1; i++, j++) {
            memcpy(mat.at(j, 0), this->at(i, x0), n);
        }

        return mat;
    }

    virtual bool save(std::ostream& os) {
        auto cols = this->cols();
        auto rows = this->rows();
        auto type = this->type();
        void* data = this->beg();

        uint64_t data_size = this->size();
        os.write((char*)&cols, sizeof(cols));
        os.write((char*)&rows, sizeof(rows));
        os.write((char*)&type, sizeof(type));
        os.write((char*)&data_size, sizeof(data_size));
        os.write((char*)data, data_size);
        return true;
    }

    virtual bool load(std::istream& is) {
        decltype(this->cols()) cols;
        decltype(this->rows()) rows;
        decltype(this->type()) type;

        uint64_t data_size;
        is.read((char*)&cols, sizeof(cols));
        is.read((char*)&rows, sizeof(rows));
        is.read((char*)&type, sizeof(type));
        is.read((char*)&data_size, sizeof(data_size));

        if (type != this->type()) {
            return false;
        }

        this->create(rows, cols);

        if (data_size != this->size()) {
            return false;
        }

        is.read((char*)this->beg(), data_size);

        return true;
    }

    virtual bool save(const std::string& path) {
        std::ofstream ofs(path, std::ofstream::binary);

        if (!ofs) {
            return false;
        }

        return save(ofs);
    }

    virtual bool load(const std::string& path) {
        std::ifstream ifs(path, std::ofstream::binary);

        if (!ifs) {
            return false;
        }

        return load(ifs);
    }
};

}
