import numpy as np


HIST_SIZE = int(np.iinfo(np.int16).max * 1.5)
CLIP_LO = 100
CLIP_HI = 100
CLIP_LIMIT = 100
RANGE_SCALE_KEY_POINT = 175
BLEND_SHIFT = 15


def blend_fixed(prev, next_frame, prev_weight):
    w0 = int((1 << BLEND_SHIFT) * prev_weight)
    w1 = int((1 << BLEND_SHIFT) * (1.0 - prev_weight))
    half_w = 1 << (BLEND_SHIFT >> 1)
    prev_i = prev.astype(np.int32)
    next_i = next_frame.astype(np.int32)
    out = (prev_i * w0 + next_i * w1 + half_w) >> BLEND_SHIFT
    return out.astype(np.int16)


def _update_min_max_clipped(hist, clip_lo, clip_hi):
    nonzero = np.nonzero(hist)[0]
    if nonzero.size == 0:
        return 0, 0
    min_idx = int(nonzero[0])
    max_idx = int(nonzero[-1])

    skipped = hist[min_idx]
    idx = min_idx
    while skipped < clip_lo and idx < max_idx:
        idx += 1
        skipped += hist[idx]
    min_clipped = idx

    skipped = hist[max_idx]
    idx = max_idx
    while skipped < clip_hi and idx > min_idx:
        idx -= 1
        skipped += hist[idx]
    max_clipped = idx

    return min_clipped, max_clipped


def _make_lhe_map(hist, min_clipped, max_clipped, clip_limit):
    hist = hist.copy()
    if max_clipped < min_clipped:
        return np.zeros_like(hist, dtype=np.uint8)

    hist[min_clipped:max_clipped + 1] = np.minimum(
        hist[min_clipped:max_clipped + 1], clip_limit
    )
    total_clipped = int(hist[min_clipped:max_clipped + 1].sum())
    if total_clipped <= 0:
        return np.zeros_like(hist, dtype=np.uint8)

    range_size = max_clipped - min_clipped + 1
    if range_size < RANGE_SCALE_KEY_POINT:
        target_range = int(range_size * 256 / RANGE_SCALE_KEY_POINT)
    else:
        target_range = 256
    target_range = max(1, target_range)
    target_range_min = int((256 - target_range) / 2)
    target_range_max = int(target_range_min + target_range - 1)

    out_map = np.zeros(hist.size, dtype=np.uint8)
    out_map[max_clipped:] = 255

    scale = float(target_range - 1) / float(total_clipped)
    cumulative = np.cumsum(hist[min_clipped:max_clipped + 1], dtype=np.uint64)
    mapped = cumulative * scale + target_range_min
    out_map[min_clipped:max_clipped + 1] = np.clip(mapped, 0, 255).astype(np.uint8)

    scale2 = float(target_range) / float(range_size)
    idx = min_clipped - 1
    i = 0
    while idx >= 0:
        val = int(target_range_min - float(i) * scale2)
        if val < 0:
            break
        out_map[idx] = np.uint8(val)
        idx -= 1
        i += 1

    idx = max_clipped + 1
    i = 0
    while idx < out_map.size:
        val = int(target_range_max + float(i) * scale2)
        if val > 255:
            break
        out_map[idx] = np.uint8(val)
        idx += 1
        i += 1

    return out_map


def lhe_process(src):
    src_idx = np.clip(src, 0, HIST_SIZE - 1).astype(np.int32)
    hist = np.bincount(src_idx.ravel(), minlength=HIST_SIZE).astype(np.uint32)
    min_clipped, max_clipped = _update_min_max_clipped(hist, CLIP_LO, CLIP_HI)
    lut = _make_lhe_map(hist, min_clipped, max_clipped, CLIP_LIMIT)
    return lut[src_idx]


def std_calib_lhe(prev, curr, next_frame, prev_temp, curr_temp, next_temp):
    denom = float(next_temp - prev_temp)
    if denom == 0:
        prev_weight = 0.5
    else:
        prev_weight = float(curr_temp - prev_temp) / denom
    calib = blend_fixed(prev, next_frame, prev_weight)

    curr_i = curr.astype(np.int32)
    curr_i -= int(curr_i.min())
    curr_i = curr_i - calib.astype(np.int32)

    return lhe_process(curr_i)
