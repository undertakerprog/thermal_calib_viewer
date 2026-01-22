#pragma once

#include <cstdlib>
#include <cstdint>
#include <cstddef>
#include <cmath>
#include <algorithm>

namespace eye {
namespace Math {
inline size_t alignHi(size_t size, size_t align) {
    return (size + align - 1) & ~(align - 1);
}

inline void* alignHi(const void* ptr, size_t align) {
    return reinterpret_cast<void*>((reinterpret_cast<size_t>(ptr) + align - 1) & ~(align - 1));
}

inline size_t alignLo(size_t size, size_t align) {
    return size & ~(align - 1);
}

inline void* alignLo(const void* ptr, size_t align) {
    return reinterpret_cast<void*>(reinterpret_cast<size_t>(ptr) & ~(align - 1));
}

inline bool isPOT(uint64_t x) {
    return (x & (x - 1)) == 0;
}

inline float random01() {
    auto r = std::rand();
    auto v = static_cast<float>(r) / RAND_MAX;
    return v;
}

template <typename T>
inline T clamp(const T& val, const T& lo, const T& hi) {
    return std::min(std::max(val, lo), hi);
}

inline float clamp01(const float& val) {
    return clamp(val, 0.0f, 1.0f);
}

template <typename T>
inline T lerp(const T& from, const T& to, const float& amount) {
    return to * amount + from * (1.0f - amount);
}

template <typename T>
inline T sign(const T& value) {
    return (T)(value < 0 ? -1 : 1);
}

template <typename T>
inline T abs(const T& value) {
    return value < 0 ? -value : value;
}

template<typename T>
inline T max(const T& a, const T& b) {
    return a > b ? a : b;
}

template<typename T>
inline T min(const T& a, const T& b) {
    return a < b ? a : b;
}

template <typename T>
inline T moveTowards(const T& current, const T& target, const T& delta) {
    auto distance = target - current;

    if (abs(distance) <= abs(delta)) {
        return target;
    }

    auto s = sign(distance);
    return current + s * delta;
}
}
}
