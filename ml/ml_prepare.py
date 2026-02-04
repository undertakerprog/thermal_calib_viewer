import argparse
import csv
import os
from pathlib import Path

import numpy as np

from core.calib_detect import compute_diff, compute_metrics, filter_temp_outliers
from core.raw_data import read_raw_int16, read_raw_uint16, scan_raws


def canonical_base(name):
    base = name.replace('(gen)', '').strip()
    return base.rstrip('. ')


def collect_pairs(root_dir):
    good_root = os.path.join(root_dir, 'good')
    bad_root = os.path.join(root_dir, 'bad')
    pairs = []
    if not os.path.isdir(good_root) or not os.path.isdir(bad_root):
        return pairs
    for name in os.listdir(good_root):
        good_path = os.path.join(good_root, name)
        if not os.path.isdir(good_path):
            continue
        base = canonical_base(name)
        bad_path = os.path.join(bad_root, base)
        if os.path.isdir(bad_path):
            pairs.append((base, good_path, bad_path))
    return pairs


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


def build_dataset(pairs, downsample_step=2, metrics_downsample=2):
    rows = []
    for base, good_dir, bad_dir in pairs:
        good_entries, _ = scan_raws(good_dir)
        bad_entries, _ = scan_raws(bad_dir)
        if len(bad_entries) < 3:
            continue
        good_temps = {entry.temp_value for entry in good_entries}

        filtered_entries, outliers = filter_temp_outliers(bad_entries)
        if len(filtered_entries) < 3:
            continue

        frame_cache_i16 = {}
        frame_cache_u16 = {}

        def get_i16(entry):
            frame = frame_cache_i16.get(entry.path)
            if frame is None:
                frame = read_raw_int16(entry.path)
                if downsample_step > 1:
                    frame = downsample(frame, downsample_step)
                frame_cache_i16[entry.path] = frame
            return frame

        def get_u16(entry):
            frame = frame_cache_u16.get(entry.path)
            if frame is None:
                frame = read_raw_uint16(entry.path)
                if downsample_step > 1:
                    frame = downsample(frame, downsample_step)
                frame_cache_u16[entry.path] = frame
            return frame

        for i in range(len(filtered_entries) - 2):
            prev_entry = filtered_entries[i]
            curr_entry = filtered_entries[i + 1]
            next_entry = filtered_entries[i + 2]

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

            label = 1 if curr_entry.temp_value in good_temps else 0
            rows.append(
                {
                    "pair": base,
                    "temp": float(curr_entry.temp_value),
                    "temp_str": curr_entry.temp_str,
                    "label": label,
                    "diff_std": metrics["std"],
                    "diff_stripe": metrics["stripe"],
                    "diff_vignette": metrics["vignette"],
                    "diff_mean_abs": diff_mean_abs,
                    "diff_p95": diff_p95,
                    "raw_mean": raw_mean,
                    "raw_std": raw_std,
                    "raw_p1": raw_p1,
                    "raw_p99": raw_p99,
                }
            )
    return rows


def write_csv(rows, out_path):
    if not rows:
        return 0
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Prepare ML dataset from good/bad pairs.")
    base_dir = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--root",
        default=str(base_dir / "data-ml"),
        help="Root folder with good/ and bad/ subfolders.",
    )
    parser.add_argument(
        "--out",
        default=str(base_dir / "data-ml" / "dataset.csv"),
        help="Output CSV path.",
    )
    parser.add_argument("--downsample", type=int, default=2, help="Downsample factor for raw frames.")
    parser.add_argument(
        "--metrics-downsample",
        type=int,
        default=2,
        help="Extra downsample factor inside diff metrics.",
    )
    args = parser.parse_args()

    pairs = collect_pairs(args.root)
    if not pairs:
        print("No pairs found.")
        return
    rows = build_dataset(pairs, downsample_step=args.downsample, metrics_downsample=args.metrics_downsample)
    count = write_csv(rows, args.out)
    print(f"Wrote {count} rows to {args.out}")


if __name__ == "__main__":
    main()
