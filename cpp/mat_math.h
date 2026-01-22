#pragma once

#include <exception>

#include "rect.h"
#include "mat.h"
#include "math.h"

namespace eye {
namespace Math {
#define __lshift_8(res, lhs, shift) \
    res[0] = lhs[0] >> shift;       \
    res[1] = lhs[1] >> shift;       \
    res[2] = lhs[2] >> shift;       \
    res[3] = lhs[3] >> shift;       \
    res[4] = lhs[4] >> shift;       \
    res[5] = lhs[5] >> shift;       \
    res[6] = lhs[6] >> shift;       \
    res[7] = lhs[7] >> shift

#define __mul_8(res, lhs, mul, shift) \
    res[0] = (lhs[0] * mul) >> shift; \
    res[1] = (lhs[1] * mul) >> shift; \
    res[2] = (lhs[2] * mul) >> shift; \
    res[3] = (lhs[3] * mul) >> shift; \
    res[4] = (lhs[4] * mul) >> shift; \
    res[5] = (lhs[5] * mul) >> shift; \
    res[6] = (lhs[6] * mul) >> shift; \
    res[7] = (lhs[7] * mul) >> shift

#define __mla(res, lhs, mul, add, shift)  \
  res[0] = ((lhs[0] + add) * mul) >> shift; \

#define __mla_8(res, lhs, mul, add, shift)  \
    res[0] = ((lhs[0] + add) * mul) >> shift; \
    res[1] = ((lhs[1] + add) * mul) >> shift; \
    res[2] = ((lhs[2] + add) * mul) >> shift; \
    res[3] = ((lhs[3] + add) * mul) >> shift; \
    res[4] = ((lhs[4] + add) * mul) >> shift; \
    res[5] = ((lhs[5] + add) * mul) >> shift; \
    res[6] = ((lhs[6] + add) * mul) >> shift; \
    res[7] = ((lhs[7] + add) * mul) >> shift

#define __ptr_mulFp_8(res, lhs, rhs, shift) \
    res[0] = lhs[0] * rhs[0] >> shift;      \
    res[1] = lhs[1] * rhs[1] >> shift;      \
    res[2] = lhs[2] * rhs[2] >> shift;      \
    res[3] = lhs[3] * rhs[3] >> shift;      \
    res[4] = lhs[4] * rhs[4] >> shift;      \
    res[5] = lhs[5] * rhs[5] >> shift;      \
    res[6] = lhs[6] * rhs[6] >> shift;      \
    res[7] = lhs[7] * rhs[7] >> shift

#define __ptr_add_8(res, lhs, rhs) \
    res[0] = lhs[0] + rhs[0];      \
    res[1] = lhs[1] + rhs[1];      \
    res[2] = lhs[2] + rhs[2];      \
    res[3] = lhs[3] + rhs[3];      \
    res[4] = lhs[4] + rhs[4];      \
    res[5] = lhs[5] + rhs[5];      \
    res[6] = lhs[6] + rhs[6];      \
    res[7] = lhs[7] + rhs[7]

#define __ptr_sub_8(res, lhs, rhs) \
    res[0] = lhs[0] - rhs[0];      \
    res[1] = lhs[1] - rhs[1];      \
    res[2] = lhs[2] - rhs[2];      \
    res[3] = lhs[3] - rhs[3];      \
    res[4] = lhs[4] - rhs[4];      \
    res[5] = lhs[5] - rhs[5];      \
    res[6] = lhs[6] - rhs[6];      \
    res[7] = lhs[7] - rhs[7]

#define __find_max_8(max, pCur)          \
    max = pCur[0] > max ? pCur[0] : max; \
    max = pCur[1] > max ? pCur[1] : max; \
    max = pCur[2] > max ? pCur[2] : max; \
    max = pCur[3] > max ? pCur[3] : max; \
    max = pCur[4] > max ? pCur[4] : max; \
    max = pCur[5] > max ? pCur[5] : max; \
    max = pCur[6] > max ? pCur[6] : max; \
    max = pCur[7] > max ? pCur[7] : max

#define __do_8_op_rshift_with_value(ptr, op, value, rshift) \
        ptr[0] = (ptr[0] op value) >> rshift;               \
        ptr[1] = (ptr[1] op value) >> rshift;               \
        ptr[2] = (ptr[2] op value) >> rshift;               \
        ptr[3] = (ptr[3] op value) >> rshift;               \
        ptr[4] = (ptr[4] op value) >> rshift;               \
        ptr[5] = (ptr[5] op value) >> rshift;               \
        ptr[6] = (ptr[6] op value) >> rshift;               \
        ptr[7] = (ptr[7] op value) >> rshift;

#define __do_8_op_with_value(ptr, op, value) \
        ptr[0] = ptr[0] op value;            \
        ptr[1] = ptr[1] op value;            \
        ptr[2] = ptr[2] op value;            \
        ptr[3] = ptr[3] op value;            \
        ptr[4] = ptr[4] op value;            \
        ptr[5] = ptr[5] op value;            \
        ptr[6] = ptr[6] op value;            \
        ptr[7] = ptr[7] op value;

#define __do_1_op_with_mat(res, left, op, right) \
        res = left op right;

#define __do_8_op_with_mat(res, left, op, right) \
        res[0] = left[0] op right[0];            \
        res[1] = left[1] op right[1];            \
        res[2] = left[2] op right[2];            \
        res[3] = left[3] op right[3];            \
        res[4] = left[4] op right[4];            \
        res[5] = left[5] op right[5];            \
        res[6] = left[6] op right[6];            \
        res[7] = left[7] op right[7];

#define __do_8_op_rshift_with_mat(res, left, op, right, rshift) \
        res[0] = (left[0] op right[0]) >> rshift;               \
        res[1] = (left[1] op right[1]) >> rshift;               \
        res[2] = (left[2] op right[2]) >> rshift;               \
        res[3] = (left[3] op right[3]) >> rshift;               \
        res[4] = (left[4] op right[4]) >> rshift;               \
        res[5] = (left[5] op right[5]) >> rshift;               \
        res[6] = (left[6] op right[6]) >> rshift;               \
        res[7] = (left[7] op right[7]) >> rshift;

#define __do_op_rshift_with_mat(res, left, op, right, rshift) \
        res[0] = (left[0] op right[0]) >> rshift;

#define __do_op_mat_with_val_self(res, op, val, index) \
    res[index] = res[index] op val;
#define __do_op_mat_with_val(res, left, op, val, index) \
    res[index] = left[index] op val;
#define __do_op_mat_with_mat(res, left, op, right, index) \
    res[index] = left[index] op right[index];

#define __do_mul_shift_mat_with_val_self(res, val, rshift, index) \
    res[index] = (res[index] * val) >> rshift;
#define __do_mul_shift_mat_with_val(res, left, val, rshift, index) \
    res[index] = (left[index] * val) >> rshift;
#define __do_mul_shift_mat_with_mat(res, left, right, rshift, index) \
    res[index] = (left[index] * (int)(right[index] * (1 << rshift))) >> rshift;

#define __do_mla_mat_with_val(res, left, mul, add, rshift, index) \
    res[index] = (left[index] * mul + add) >> rshift;
#define __do_mla_mat_with_mat(res, left, mul, add, rshift, index) \
    res[index] = (left[index] * right[index] + add) >> rshift;

#define __do_find_min(min, mat, index) \
    min = mat[index] < min ? mat[index] : min;
#define __do_find_max(max, mat, index) \
    max = mat[index] > max ? mat[index] : max;

#define __find_min_8(min, pCur)          \
    min = pCur[0] < min ? pCur[0] : min; \
    min = pCur[1] < min ? pCur[1] : min; \
    min = pCur[2] < min ? pCur[2] : min; \
    min = pCur[3] < min ? pCur[3] : min; \
    min = pCur[4] < min ? pCur[4] : min; \
    min = pCur[5] < min ? pCur[5] : min; \
    min = pCur[6] < min ? pCur[6] : min; \
    min = pCur[7] < min ? pCur[7] : min

template <typename T>
T min(const Mat<T>& mat) {
    auto cur  = mat.first();
    auto last = mat.last();

    T min = *cur;

    while (cur < last) {
        min = *cur < min ? *cur : min;
        ++cur;
    }

    return min;
}

template <typename T>
T max(const Mat<T>& mat) {
    auto cur = mat.first();
    auto last = mat.last();
    T max = *cur;

    while (cur < last) {
        max = *cur > max ? *cur : max;
        ++cur;
    }

    return max;
}

template <typename T>
float avg(const Mat<T>& mat) {
    auto step = mat.total() / 4;
    auto p0 = mat.first();
    auto p1 = mat.first() + step;
    auto p2 = mat.first() + 2 * step;
    auto p3 = mat.first() + 3 * step;
    auto last = mat.last();

    int64_t t0 = 0, t1 = 0, t2 = 0, t3 = 0; //, t4 = 0, t5 = 0, t6 = 0, t7 = 0;

    while (p3 < last) {
        t0 += *p0;
        t1 += *p1;
        t2 += *p2;
        t3 += *p3;
        ++p0;
        ++p1;
        ++p2;
        ++p3;
    }

    auto avg = (float)(t0 + t1 + t2 + t3) / mat.total();
    return avg;
}

template <typename T>
float avg(const Mat<T>& mat, const Rect& roi) {
    int64_t sum = 0;
    auto tl = roi.tl();
    auto br = roi.br();

    for (int y = tl.y; y < br.y; y++) {
        auto ptr = mat.first() + mat.cols() * y + tl.x;
        auto end = ptr + roi.width;

        while (ptr < end) {
            sum += *ptr;
            ++ptr;
        }
    }

    auto avg = (float)(sum) / (roi.width * roi.height);
    return avg;
}

template <typename T>
T avgByHistogram(const Mat<T> & hist) {
    uint64_t sum = 0;
    uint64_t weightedSum = 0;

    T * pHist = hist.first();
    T * pEnd  = hist.last();

    uint32_t i = 0;

    while (pHist != pEnd) {
        sum += *pHist;
        weightedSum += *pHist++ * i++;
    }

    return weightedSum / sum;
}

template <typename T>
float stdDev(const Mat<T>& mat, float mean) {
    auto ptr = mat.first();
    auto end = mat.last();
    uint32_t sum = 0;

    while (ptr < end) {
        sum += (*ptr - mean) * (*ptr - mean);
        ++ptr;
    }

    auto dev = sqrt((float)sum / (mat.total() - 1));
    return dev;
}

template <typename T>
float stdDev(const Mat<T>& mat) {
    auto mean = avg(mat);
    return stdDev(mat, mean);
}

template <typename T>
void meanStdDev(const Mat<T>& mat, float& mean, float& dev) {
    mean = avg(mat);
    dev = stdDev(mat, mean);
}

template <typename T>
void minMax(const Mat<T>& mat, T& min, T& max) {
    auto cur = mat.first();
    auto last = mat.last();

    min = *cur;
    max = *cur;

    while (cur < last) {
        min = *cur < min ? *cur : min;
        max = *cur > max ? *cur : max;
        ++cur;
    }
}

template <typename T>
void minMaxAvg(const Mat<T>& mat, T& min, T& max, T& avg) {
    auto cur = mat.first();
    auto last = mat.last();
    min = *cur;
    max = *cur;
    int64_t total = 0;

    while (cur < last) {
        min = *cur < min ? *cur : min;
        max = *cur > max ? *cur : max;
        total += *cur;
        ++cur;
    }

    avg = total / mat.total();
    // Logger::i("Old: Sum = %llu", total);
}

template <typename T>
void lshift(const Mat<T>& in, Mat<T>& out, int shift) {
    if (in.beg() == out.beg()) {
        auto ptr = in.first();
        auto last = in.last();

        while (ptr < last) {
            __lshift_8(ptr, ptr, shift);
            ptr += 8;
        }
    } else {
        out.create(in);

        auto src = in.first();
        auto dst = out.first();
        auto last = out.last();

        while (dst < last) {
            __lshift_8(dst, src, shift);
            dst += 8;
            src += 8;
        }
    }
}

template <typename T>
void add(Mat<T>& inOut, T value) {
    auto ptr = inOut.first();
    auto last1 = inOut.last();
    auto last8 = ptr + Math::alignLo(inOut.total(), 8);

    while (ptr < last8) {
        ptr[0] = ptr[0] + value;
        ptr[1] = ptr[1] + value;
        ptr[2] = ptr[2] + value;
        ptr[3] = ptr[3] + value;
        ptr[4] = ptr[4] + value;
        ptr[5] = ptr[5] + value;
        ptr[6] = ptr[6] + value;
        ptr[7] = ptr[7] + value;
        ptr += 8;
    }

    while (ptr < last1) {
        *ptr += value;
        ++ptr;
    }
}

template <typename TIn, typename TOut>
void add(const Mat<TIn>& in, Mat<TOut>& out, TIn value) {
    out.create(in);
    auto src = in.first();
    auto res = out.first();
    auto last1 = out.last();
    auto last8 = res + Math::alignLo(out.total(), 8);

    while (res < last8) {
        res[0] = src[0] + value;
        res[1] = src[1] + value;
        res[2] = src[2] + value;
        res[3] = src[3] + value;
        res[4] = src[4] + value;
        res[5] = src[5] + value;
        res[6] = src[6] + value;
        res[7] = src[7] + value;
        src += 8;
        res += 8;
    }

    while (res < last1) {
        *res = *src + value;
        ++src;
        ++res;
    }
}

template <typename TInOut>
void addMul(Mat<TInOut>& inOut, const Mat<TInOut>& addition, const float factor) {
    auto p = addition.first();
    auto res = inOut.first();
    auto last1 = inOut.last();
    auto last8 = res + Math::alignLo(inOut.total(), 8);

    while (res < last8) {
        res[0] += p[0] * factor;
        res[1] += p[1] * factor;
        res[2] += p[2] * factor;
        res[3] += p[3] * factor;
        res[4] += p[4] * factor;
        res[5] += p[5] * factor;
        res[6] += p[6] * factor;
        res[7] += p[7] * factor;
        res += 8;
        p   += 8;
    }

    while (res < last1) {
        *res += *p * factor;
        ++res;
        ++p;
    }
}

template <typename T>
void sub(Mat<T>& inOut, T value) {
    add(inOut, (T)(-value));
}

template <typename TIn, typename TOut>
void sub(const Mat<TIn>& in, Mat<TOut>& out, TIn value) {
    add(in, out, (TIn)(-value));
}

template <typename TLeft, typename TRight, typename TDst>
void add(const Mat<TLeft>& left, const Mat<TRight>& right, Mat<TDst>& out) {
    if (!left.isSameSize(right)) {
        throw std::invalid_argument("eye::Math::add(): Mat sizes not equal!");
    }

    out.create(left);

    auto res = out.first();
    auto lhs = left.first();
    auto rhs = right.first();
    auto last1 = out.last();
    auto last8 = res + Math::alignLo(out.total(), 8);

    while (res < last8) {
        __do_op_mat_with_mat(res, lhs, +, rhs, 0);
        __do_op_mat_with_mat(res, lhs, +, rhs, 1);
        __do_op_mat_with_mat(res, lhs, +, rhs, 2);
        __do_op_mat_with_mat(res, lhs, +, rhs, 3);
        __do_op_mat_with_mat(res, lhs, +, rhs, 4);
        __do_op_mat_with_mat(res, lhs, +, rhs, 5);
        __do_op_mat_with_mat(res, lhs, +, rhs, 6);
        __do_op_mat_with_mat(res, lhs, +, rhs, 7);
        res += 8;
        lhs += 8;
        rhs += 8;
    }

    while (res < last1) {
        __do_op_mat_with_mat(res, lhs, +, rhs, 0);
        ++res;
        ++lhs;
        ++rhs;
    }
}

template <typename TInOut, typename TAdd>
void add(Mat<TInOut>& inOut, const Mat<TAdd>& right) noexcept {
    if (!inOut.isSameSize(right)) {
        throw std::invalid_argument("eye::Math::add(): Mat sizes not equal!");
    }

    auto pInOut = inOut.first();
    auto pRight = right.first();
    auto pEnd1  = inOut.last();
    auto pEnd8  = pInOut + Math::alignLo(inOut.total(), 8);

    while (pInOut != pEnd8) {
        pInOut[0] += pRight[0];
        pInOut[1] += pRight[1];
        pInOut[2] += pRight[2];
        pInOut[3] += pRight[3];
        pInOut[4] += pRight[4];
        pInOut[5] += pRight[5];
        pInOut[6] += pRight[6];
        pInOut[7] += pRight[7];
        pInOut += 8;
        pRight += 8;
    }

    while (pInOut != pEnd1) {
        pInOut[0] += pRight[0];
        pInOut += 1;
        pRight += 1;
    }
}

template <typename TLeft, typename TRight, typename TDst>
void addAndDivBy2(const Mat<TLeft>& left, const Mat<TRight>& right, Mat<TDst>& out) {
    if (!left.isSameSize(right)) {
        throw std::invalid_argument("eye::Math::addAndDivBy2(): Mat sizes not equal!");
    }

    out.create(left);

    auto res = out.first();
    auto lhs = left.first();
    auto rhs = right.first();
    auto last1 = out.last();
    auto last8 = res + Math::alignLo(out.total(), 8);

    while (res < last8) {
        __do_8_op_rshift_with_mat(res, lhs, +, rhs, 1);
        res += 8;
        lhs += 8;
        rhs += 8;
    }

    while (res < last1) {
        __do_op_rshift_with_mat(res, lhs, +, rhs, 1);
        ++res;
        ++lhs;
        ++rhs;
    }
}

template <typename TLeft, typename TRight, typename TDst>
void sub(const Mat<TLeft>& left, const Mat<TRight>& right, Mat<TDst>& out) {
    if (!left.isSameSize(right)) {
        throw std::invalid_argument("eye::Math::sub(): Mat sizes not equal!");
    }

    out.create(left);

    auto res = out.first();
    auto lhs = left.first();
    auto rhs = right.first();
    auto last1 = out.last();
    auto last8 = res + Math::alignLo(out.total(), 8);

    while (res < last8) {
        __do_op_mat_with_mat(res, lhs, -, rhs, 0);
        __do_op_mat_with_mat(res, lhs, -, rhs, 1);
        __do_op_mat_with_mat(res, lhs, -, rhs, 2);
        __do_op_mat_with_mat(res, lhs, -, rhs, 3);
        __do_op_mat_with_mat(res, lhs, -, rhs, 4);
        __do_op_mat_with_mat(res, lhs, -, rhs, 5);
        __do_op_mat_with_mat(res, lhs, -, rhs, 6);
        __do_op_mat_with_mat(res, lhs, -, rhs, 7);
        res += 8;
        lhs += 8;
        rhs += 8;
    }

    while (res < last1) {
        __do_op_mat_with_mat(res, lhs, -, rhs, 0);
        ++res;
        ++lhs;
        ++rhs;
    }
}

template <typename TSrc, typename TDst>
void mulFp(const Mat<TSrc>& src, Mat<TDst>& out, float mul, int rshift = 15) {
    out.create(src);

    auto res = out.first();
    auto lhs = src.first();
    int rhs = mul * (1 << rshift);
    auto last1 = out.last();
    auto last8 = res + Math::alignLo(out.total(), 8);

    while (res < last8) {
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 0);
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 1);
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 2);
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 3);
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 4);
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 5);
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 6);
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 7);
        res += 8;
        lhs += 8;
    }

    while (res < last1) {
        __do_mul_shift_mat_with_val(res, lhs, rhs, rshift, 0);
        ++res;
        ++lhs;
    }
}

template <typename TSrc0, typename TSrc1, typename TDst>
void mulFp(const Mat<TSrc0>& left, const Mat<TSrc1>& right, Mat<TDst>& out, int rshift = 15) {
    if (!left.isSameSize(right)) {
        throw std::invalid_argument("eye::Math::mulFp(): Mat sizes not equal!");
    }

    out.create(left);

    auto res = out.first();
    auto lhs = left.first();
    auto rhs = right.first();

    auto last1 = out.last();
    auto last8 = res + Math::alignLo(out.total(), 8);

    while (res < last8) {
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 0);
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 1);
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 2);
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 3);
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 4);
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 5);
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 6);
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 7);
        res += 8;
        lhs += 8;
        rhs += 8;
    }

    while (res < last1) {
        __do_mul_shift_mat_with_mat(res, lhs, rhs, rshift, 0);
        ++res;
        ++lhs;
        ++rhs;
    }
}

template <typename Tin, typename Tout>
void changeType(const Mat<Tin>& in, Mat<Tout>& out) {
    out.create(in);
    auto dst = out.first();
    auto src = in.first();
    auto last1 = out.last();
    auto last8 = dst + Math::alignLo(out.total(), 8);

    while (dst < last8) {
        dst[0] = static_cast<Tout>(src[0]);
        dst[1] = static_cast<Tout>(src[1]);
        dst[2] = static_cast<Tout>(src[2]);
        dst[3] = static_cast<Tout>(src[3]);
        dst[4] = static_cast<Tout>(src[4]);
        dst[5] = static_cast<Tout>(src[5]);
        dst[6] = static_cast<Tout>(src[6]);
        dst[7] = static_cast<Tout>(src[7]);
        src += 8;
        dst += 8;
    }

    while (dst < last1) {
        *dst = static_cast<Tout>(*src);
        ++dst;
        ++src;
    }
}

template <typename TSrc, typename TDst>
void convert(const Mat<TSrc>& in, Mat<TDst>& out, float scale, int32_t offset, int32_t shift = 15) {
    if (scale < 0) {
        throw;
    }

    if (offset == 0 && scale == 1.0f) {
        changeType(in, out);
    } else if (offset == 0) {
        mulFp(in, out, scale, shift);
    } else if (scale == 1.0f) {
        Math::sub(in, out, (TSrc)offset);
    } else {
        const int32_t fpScale  = (1 << shift) * scale;
        out.create(in.rows(), in.cols());
        auto src = in.first();
        auto dst = out.first();
        auto last1 = out.last();
        auto last8 = dst + Math::alignLo(out.total(), 8);

        while (dst < last8) {
            __mla_8(dst, src, fpScale, -offset, shift);
            dst += 8;
            src += 8;
        }

        while (dst < last1) {
            __mla(dst, src, fpScale, -offset, shift);
            ++dst;
            ++src;
        }
    }
}

template <typename T>
void convertToU8(const Mat<T>& in, Mat<uint8_t>& out, int32_t min, int32_t max) {
    out.create(in.rows(), in.cols());

    if (min >= max) {
        out.setTo(0);
        return;
    }

    int32_t range = max - min;
    float scale = range > 255.0 ? 255.0 / range : 1.0;
    int offset = min;
    convert(in, out, scale, offset, 15);
}

template <typename T>
void convertToU8(const Mat<T>& in, Mat<uint8_t>& out) {
    T min = 0;
    T max = 0;
    minMax(in, min, max);
    return convertToU8(in, out, min, max);
}

template <typename T>
void blend(const Mat<T>& img0, float alpha, const Mat<T>& img1, float beta, Mat<T>& out, int shift = 15) {
    out.create(img0);
    int32_t w0 = (1 << shift) * alpha;
    int32_t w1 = (1 << shift) * beta;
    int32_t halfW = 1 << (shift >> 1);

    auto i0 = img0.first();
    auto i1 = img1.first();
    auto res = out.first();
    auto last = out.last();

    while (res < last) {
        *res = ((*i0 * w0 + *i1 * w1 + halfW) >> shift);
        ++res;
        ++i0;
        ++i1;
    }
}

template <typename T>
void bitwise_xor(Mat<T>& inOut, T value) {
    auto dst = inOut.first();
    auto last1 = inOut.last();
    auto last8 = dst + Math::alignLo(inOut.total(), 8);

    while (dst < last8) {
        __do_op_mat_with_val_self(dst, ^, value, 0);
        __do_op_mat_with_val_self(dst, ^, value, 1);
        __do_op_mat_with_val_self(dst, ^, value, 2);
        __do_op_mat_with_val_self(dst, ^, value, 3);
        __do_op_mat_with_val_self(dst, ^, value, 4);
        __do_op_mat_with_val_self(dst, ^, value, 5);
        __do_op_mat_with_val_self(dst, ^, value, 6);
        __do_op_mat_with_val_self(dst, ^, value, 7);
        dst += 8;
    }

    while (dst < last1) {
        __do_op_mat_with_val_self(dst, ^, value, 0);
        ++dst;
    }
}

template <typename TIn, typename TOut>
void mapImage(Mat<TIn>& input, Mat<TOut> & out, Mat<TOut> & map) {
    out.create(input);

    auto pSrc = input.first();
    auto pEnd = input.last();
    auto pDst = out.first();
    auto pMap = map.first();

    while (pSrc < pEnd) {
        pDst[0] = pMap[pSrc[0]];
        pDst[1] = pMap[pSrc[1]];
        pDst[2] = pMap[pSrc[2]];
        pDst[3] = pMap[pSrc[3]];
        pSrc += 4;
        pDst += 4;
    }
}

} // Math
} // eye


