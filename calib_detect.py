import numpy as np

from std_calib import blend_fixed


MAD_SCALE = 1.4826


def compute_diff(prev, curr, next_frame, prev_temp, curr_temp, next_temp):
    denom = float(next_temp - prev_temp)
    if denom == 0:
        prev_weight = 0.5
    else:
        prev_weight = float(curr_temp - prev_temp) / denom
    calib = blend_fixed(prev, next_frame, prev_weight)
    curr_i = curr.astype(np.int32)
    curr_i -= int(curr_i.min())
    diff = curr_i - calib.astype(np.int32)
    return diff


def _radial_profile(img):
    h, w = img.shape
    y, x = np.indices((h, w))
    cy = (h - 1) / 2.0
    cx = (w - 1) / 2.0
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.int32)
    max_r = int(r.max()) + 1
    tbin = np.bincount(r.ravel(), img.ravel(), minlength=max_r)
    nr = np.bincount(r.ravel(), minlength=max_r)
    nr = np.maximum(nr, 1)
    return tbin / nr


def compute_metrics(diff, downsample=2, smooth_window=21):
    if downsample > 1:
        diff = diff[::downsample, ::downsample]

    diff = diff.astype(np.float32)
    std_val = float(np.std(diff))

    col_mean = diff.mean(axis=0)
    if smooth_window > 1:
        kernel = np.ones(smooth_window, dtype=np.float32) / smooth_window
        smooth = np.convolve(col_mean, kernel, mode="same")
    else:
        smooth = col_mean
    stripe_val = float(np.std(col_mean - smooth))

    profile = _radial_profile(diff)
    vignette_val = float(np.ptp(profile))

    return {
        "std": std_val,
        "stripe": stripe_val,
        "vignette": vignette_val,
    }


def compute_metric_series(entries, get_frame_i16):
    series = {"std": [], "stripe": [], "vignette": []}
    temps = []
    for i in range(len(entries) - 2):
        prev = entries[i]
        curr = entries[i + 1]
        next_frame = entries[i + 2]
        diff = compute_diff(
            get_frame_i16(prev),
            get_frame_i16(curr),
            get_frame_i16(next_frame),
            prev.temp_value,
            curr.temp_value,
            next_frame.temp_value,
        )
        metrics = compute_metrics(diff)
        for key in series:
            series[key].append(metrics[key])
        temps.append(float(curr.temp_value))
    return series, temps


def _robust_stats(values):
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return 0.0, 1.0
    cutoff = np.percentile(arr, 30)
    baseline = arr[arr <= cutoff] if arr.size >= 5 else arr
    median = float(np.median(baseline))
    mad = float(np.median(np.abs(baseline - median)))
    if mad == 0:
        mad = float(np.median(np.abs(arr - np.median(arr))))
    if mad == 0:
        mad = 1.0
    return median, mad


def combine_scores(metric_series, weights=None):
    if weights is None:
        weights = {"std": 0.5, "stripe": 1.0, "vignette": 1.0}
    med_mad = {}
    for key, values in metric_series.items():
        med_mad[key] = _robust_stats(values)

    length = len(next(iter(metric_series.values()))) if metric_series else 0
    scores = []
    for idx in range(length):
        score = 0.0
        for key, values in metric_series.items():
            median, mad = med_mad[key]
            z = (values[idx] - median) / (mad * MAD_SCALE)
            if z > 0:
                score += weights.get(key, 1.0) * z
        scores.append(score)
    return scores, med_mad


def filter_temp_outliers(entries):
    if len(entries) < 3:
        return entries, []
    temps = np.array([float(e.temp_value) for e in entries], dtype=np.float64)
    median = float(np.median(temps))
    q1, q3 = np.percentile(temps, (25, 75))
    iqr = q3 - q1
    if iqr == 0:
        iqr = 10.0
    high_lim = max(median + 6 * iqr, 200.0)
    low_lim = min(median - 6 * iqr, -200.0)

    outlier_idx = set(i for i, t in enumerate(temps) if t > high_lim or t < low_lim)

    steps = np.diff(temps)
    if steps.size:
        med_step = float(np.median(np.abs(steps)))
        if med_step == 0:
            med_step = 1.0
        if abs(steps[-1]) > 5 * med_step:
            outlier_idx.add(len(temps) - 1)

    outliers = [entries[i] for i in sorted(outlier_idx)]
    filtered = [e for i, e in enumerate(entries) if i not in outlier_idx]
    return filtered, outliers


def _find_streak(scores, temps, threshold, start_temp, streak):
    count = 0
    start_idx = None
    for i, score in enumerate(scores):
        if temps[i] < start_temp:
            count = 0
            start_idx = None
            continue
        if score >= threshold:
            if start_idx is None:
                start_idx = i
            count += 1
            if count >= streak:
                return start_idx
        else:
            count = 0
            start_idx = None
    return None


def _adjust_onset(scores, onset_idx, threshold, lookback=2, frac=0.7):
    if onset_idx is None or onset_idx <= 0:
        return onset_idx
    low = max(0, onset_idx - lookback)
    target = threshold * frac
    for idx in range(onset_idx - 1, low - 1, -1):
        if scores[idx] >= target:
            onset_idx = idx
    return onset_idx


def _shift_left_by_low_threshold(scores, onset_idx, threshold, min_frac=0.6, max_back=2):
    if onset_idx is None:
        return None
    low = max(0, onset_idx - max_back)
    low_thresh = threshold * min_frac
    best = onset_idx
    for idx in range(onset_idx - 1, low - 1, -1):
        if scores[idx] >= low_thresh:
            best = idx
        else:
            break
    return best


def _find_trend_onset(scores, temps, start_temp, end_idx, low_thresh, trend_len=2):
    if end_idx is None:
        return None
    start_idx = None
    for i, t in enumerate(temps):
        if t >= start_temp:
            start_idx = i
            break
    if start_idx is None:
        return None

    end_idx = min(end_idx, len(scores) - 1)
    for i in range(start_idx, end_idx + 1):
        if scores[i] < low_thresh:
            continue
        ok = True
        for k in range(1, trend_len + 1):
            j = i + k
            if j > end_idx:
                break
            if scores[j] < scores[j - 1]:
                ok = False
                break
        if ok:
            return i
    return None


def _has_temp_in_range(temps, low, high):
    for t in temps:
        if low <= t < high:
            return True
    return False


def detect_bad(entries, get_frame_i16, start_temp=50.0, streak=3):
    filtered, outliers = filter_temp_outliers(entries)
    if len(filtered) < 3:
        return {
            "bad_idx": None,
            "bad_entry": None,
            "reason": "not_enough_frames",
            "outliers": outliers,
            "threshold": None,
            "baseline": None,
        }

    metric_series, temps = compute_metric_series(filtered, get_frame_i16)
    scores, med_mad = combine_scores(metric_series)

    if not scores:
        return {
            "bad_idx": None,
            "bad_entry": None,
            "reason": "no_scores",
            "outliers": outliers,
            "threshold": None,
            "baseline": None,
        }

    baseline = float(np.median(scores))
    mad = float(np.median(np.abs(np.array(scores) - baseline)))
    if mad == 0:
        mad = 1.0

    threshold_normal = baseline + 3.5 * mad
    threshold_defect = baseline + 8.0 * mad

    # early defect: only if extremely strong deviation
    for i, score in enumerate(scores):
        if temps[i] < start_temp and score >= threshold_defect:
            return {
                "bad_idx": i,
                "bad_entry": filtered[i + 1],
                "reason": "early_defect",
                "score": score,
                "threshold": threshold_defect,
                "baseline": baseline,
                "outliers": outliers,
            }

    # normal onset: sustained increase after start_temp
    streak_idx = _find_streak(scores, temps, threshold_normal, start_temp, streak)
    if streak_idx is not None:
        trend_idx = _find_trend_onset(
            scores,
            temps,
            start_temp,
            streak_idx,
            low_thresh=threshold_normal * 0.6,
            trend_len=2,
        )
        if trend_idx is not None:
            onset_idx = trend_idx
        else:
            onset_idx = _adjust_onset(scores, streak_idx, threshold_normal, lookback=2, frac=0.7)
            onset_idx = _shift_left_by_low_threshold(scores, onset_idx, threshold_normal, min_frac=0.6, max_back=2)
        if onset_idx >= streak_idx:
            onset_idx = max(0, streak_idx - 2)
        # If the detected onset falls below 53C and there are no 52.xx frames,
        # push it to the first available frame >= 53C to avoid large early shifts.
        if temps[onset_idx] < 53.0 and not _has_temp_in_range(temps, 52.0, 53.0):
            for i, t in enumerate(temps):
                if t >= 53.0:
                    onset_idx = i
                    break
        return {
            "bad_idx": onset_idx,
            "bad_entry": filtered[onset_idx + 1],
            "reason": "sustained_after_start",
            "score": scores[onset_idx],
            "threshold": threshold_normal,
            "baseline": baseline,
            "outliers": outliers,
        }

    return {
        "bad_idx": None,
        "bad_entry": None,
        "reason": "no_bad",
        "score": None,
        "threshold": threshold_normal,
        "baseline": baseline,
        "outliers": outliers,
    }
