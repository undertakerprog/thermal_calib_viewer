import argparse
import pickle
from pathlib import Path

import numpy as np

from core.calib_detect import compute_diff, compute_metrics
from core.raw_data import read_raw_int16, read_raw_uint16, scan_raws


def downsample(frame, step):
    if step <= 1:
        return frame
    return frame[::step, ::step]


def compute_raw_stats(frame_u16):
    frame = frame_u16.astype(np.float32)
    mean = float(np.mean(frame))
    std = float(np.std(frame))
    p1 = float(np.percentile(frame, 1))
    p99 = float(np.percentile(frame, 99))
    return mean, std, p1, p99


def compute_diff_stats(diff):
    diff = diff.astype(np.float32)
    abs_diff = np.abs(diff)
    mean_abs = float(np.mean(abs_diff))
    p95 = float(np.percentile(abs_diff, 95))
    return mean_abs, p95


def build_features(entries, downsample_step=2, metrics_downsample=2):
    features = []
    temps = []
    if len(entries) < 3:
        return features, temps

    cache_i16 = {}
    cache_u16 = {}

    def get_i16(entry):
        frame = cache_i16.get(entry.path)
        if frame is None:
            frame = read_raw_int16(entry.path)
            if downsample_step > 1:
                frame = downsample(frame, downsample_step)
            cache_i16[entry.path] = frame
        return frame

    def get_u16(entry):
        frame = cache_u16.get(entry.path)
        if frame is None:
            frame = read_raw_uint16(entry.path)
            if downsample_step > 1:
                frame = downsample(frame, downsample_step)
            cache_u16[entry.path] = frame
        return frame

    for i in range(len(entries) - 2):
        prev_entry = entries[i]
        curr_entry = entries[i + 1]
        next_entry = entries[i + 2]
        diff = compute_diff(
            get_i16(prev_entry),
            get_i16(curr_entry),
            get_i16(next_entry),
            prev_entry.temp_value,
            curr_entry.temp_value,
            next_entry.temp_value,
        )
        metrics = compute_metrics(diff, downsample=metrics_downsample)
        diff_mean_abs, diff_p95 = compute_diff_stats(diff)
        raw_mean, raw_std, raw_p1, raw_p99 = compute_raw_stats(get_u16(curr_entry))

        features.append(
            [
                metrics["std"],
                metrics["stripe"],
                metrics["vignette"],
                diff_mean_abs,
                diff_p95,
                raw_mean,
                raw_std,
                raw_p1,
                raw_p99,
            ]
        )
        temps.append(float(curr_entry.temp_value))
    return features, temps


def find_first_bad(temps, probs, threshold=0.5, start_temp=50.0):
    for temp, prob in zip(temps, probs):
        if temp >= start_temp and prob >= threshold:
            return temp, prob
    return None, None


def main():
    parser = argparse.ArgumentParser(description="Predict bad onset using trained ML model.")
    base_dir = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--model",
        default=str(base_dir / "data-ml" / "model.pkl"),
        help="Trained model path.",
    )
    parser.add_argument("--folder", required=True, help="Folder with raw frames.")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--start-temp", type=float, default=50.0)
    parser.add_argument("--downsample", type=int, default=2)
    parser.add_argument("--metrics-downsample", type=int, default=2)
    args = parser.parse_args()

    with open(args.model, "rb") as handle:
        payload = pickle.load(handle)
    model = payload["model"]

    entries, _ = scan_raws(args.folder)
    features, temps = build_features(entries, args.downsample, args.metrics_downsample)
    if not features:
        print("Not enough frames.")
        return
    probs = model.predict_proba(np.array(features))[:, 0]
    bad_temp, bad_prob = find_first_bad(temps, probs, threshold=args.threshold, start_temp=args.start_temp)
    if bad_temp is None:
        print("ML: no bad frames detected.")
    else:
        print(f"ML: bad from {bad_temp:.2f} (prob {bad_prob:.3f})")


if __name__ == "__main__":
    main()
