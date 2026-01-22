#pragma once

#include "point.h"
#include <algorithm>

namespace eye {
template <typename T>
class Rect_ {
public:
    T x, y, width, height; //< the top-left corner, as well as width and height of the rectangle

    //! various constructors
    Rect_();
    Rect_(T x, T y, T width, T height);
    Rect_(const Rect_& r);
    Rect_(const Point_<T>& pt1, const Point_<T>& pt2);
    Rect_& operator=(const Rect_& r);
    //! the top-left corner
    Point_<T> tl() const;
    //! the bottom-right corner
    Point_<T> br() const;
    //! size (width, height) of the rectangle
    Point_<T> size() const;
    //! area (width*height) of the rectangle
    T area() const;
    //! conversion to another data type
    template <typename T2>
    operator Rect_<T2>() const;
    //! checks whether the rectangle contains the point
    bool contains(const Point_<T>& pt) const;
};

typedef Rect_<int> Rect2i;
typedef Rect_<float> Rect2f;
typedef Rect_<double> Rect2d;
typedef Rect2i Rect;

template <typename T>
inline Rect_<T>::Rect_()
    : x(0)
    , y(0)
    , width(0)
    , height(0) {
}

template <typename T>
inline Rect_<T>::Rect_(T _x, T _y, T _width, T _height)
    : x(_x)
    , y(_y)
    , width(_width)
    , height(_height) {
}

template <typename T>
inline Rect_<T>::Rect_(const Rect_<T>& r)
    : x(r.x)
    , y(r.y)
    , width(r.width)
    , height(r.height) {
}

template <typename T>
inline Rect_<T>::Rect_(const Point_<T>& pt1, const Point_<T>& pt2) {
    x = std::min(pt1.x, pt2.x);
    y = std::min(pt1.y, pt2.y);
    width = std::max(pt1.x, pt2.x) - x;
    height = std::max(pt1.y, pt2.y) - y;
}

template <typename T>
inline Rect_<T>& Rect_<T>::operator=(const Rect_<T>& r) {
    x = r.x;
    y = r.y;
    width = r.width;
    height = r.height;
    return *this;
}

template <typename T>
inline Point_<T> Rect_<T>::tl() const {
    return Point_<T>(x, y);
}

template <typename T>
inline Point_<T> Rect_<T>::br() const {
    return Point_<T>(x + width, y + height);
}

template <typename T>
inline Point_<T> Rect_<T>::size() const {
    return Point_<T>(width, height);
}

template <typename T>
inline T Rect_<T>::area() const {
    return width * height;
}

template <typename T>
template <typename T2>
inline Rect_<T>::operator Rect_<T2>() const {
    throw;
    //return Rect_<T2>(saturate_cast<T2>(x), saturate_cast<T2>(y), saturate_cast<T2>(width), saturate_cast<T2>(height));
}

template <typename T>
inline bool Rect_<T>::contains(const Point_<T>& pt) const {
    return x <= pt.x && pt.x < x + width && y <= pt.y && pt.y < y + height;
}

template <typename T>
static inline Rect_<T>& operator+=(Rect_<T>& a, const Point_<T>& b) {
    a.x += b.x;
    a.y += b.y;
    return a;
}

template <typename T>
static inline Rect_<T>& operator-=(Rect_<T>& a, const Point_<T>& b) {
    a.x -= b.x;
    a.y -= b.y;
    return a;
}
template <typename T>
static inline Rect_<T>& operator&=(Rect_<T>& a, const Rect_<T>& b) {
    T x1 = std::max(a.x, b.x);
    T y1 = std::max(a.y, b.y);
    a.width = std::min(a.x + a.width, b.x + b.width) - x1;
    a.height = std::min(a.y + a.height, b.y + b.height) - y1;
    a.x = x1;
    a.y = y1;

    if (a.width <= 0 || a.height <= 0) {
        a = Rect();
    }

    return a;
}

template <typename T>
static inline Rect_<T>& operator|=(Rect_<T>& a, const Rect_<T>& b) {
    T x1 = std::min(a.x, b.x);
    T y1 = std::min(a.y, b.y);
    a.width = std::max(a.x + a.width, b.x + b.width) - x1;
    a.height = std::max(a.y + a.height, b.y + b.height) - y1;
    a.x = x1;
    a.y = y1;
    return a;
}

template <typename T>
static inline bool operator==(const Rect_<T>& a, const Rect_<T>& b) {
    return a.x == b.x && a.y == b.y && a.width == b.width && a.height == b.height;
}

template <typename T>
static inline bool operator!=(const Rect_<T>& a, const Rect_<T>& b) {
    return a.x != b.x || a.y != b.y || a.width != b.width || a.height != b.height;
}

template <typename T>
static inline Rect_<T> operator+(const Rect_<T>& a, const Point_<T>& b) {
    return Rect_<T>(a.x + b.x, a.y + b.y, a.width, a.height);
}

template <typename T>
static inline Rect_<T> operator-(const Rect_<T>& a, const Point_<T>& b) {
    return Rect_<T>(a.x - b.x, a.y - b.y, a.width, a.height);
}

template <typename T>
static inline Rect_<T> operator&(const Rect_<T>& a, const Rect_<T>& b) {
    Rect_<T> c = a;
    return c &= b;
}

template <typename T>
static inline Rect_<T> operator|(const Rect_<T>& a, const Rect_<T>& b) {
    Rect_<T> c = a;
    return c |= b;
}
}
