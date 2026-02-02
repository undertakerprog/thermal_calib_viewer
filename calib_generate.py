import os
import shutil
from decimal import Decimal, ROUND_HALF_UP

import numpy as np


def convert_celsius_to_adc(temp_c):
    v = (float(temp_c) - 478.17) / (-207.9)
    v = ((v - 0.5) * 0.75) + 0.6
    adc_max_value = (np.iinfo(np.int16).max >> 1)
    adc_to_v = 2.0 / adc_max_value
    adc_value = int((v - 0.5) / adc_to_v)
    adc_value = adc_max_value - adc_value
    return int(np.clip(adc_value, 0, adc_max_value))


def write_fpa_image(path, frame_i16, temp_c):
    rows, cols = frame_i16.shape
    t_adc = np.float32(float(convert_celsius_to_adc(temp_c)))
    mat_type = np.int32(3)
    data_size = np.uint64(rows * cols * 2)
    header = b"".join(
        [
            t_adc.tobytes(),
            np.int32(cols).tobytes(),
            np.int32(rows).tobytes(),
            mat_type.tobytes(),
            data_size.tobytes(),
        ]
    )
    with open(path, "wb") as handle:
        handle.write(header)
        handle.write(frame_i16.astype("<i2", copy=False).tobytes())


def _interp_linear(temp, t0, f0, t1, f1):
    if t1 == t0:
        return f0
    alpha = (temp - t0) / (t1 - t0)
    return f0 + (f1 - f0) * alpha


def _fit_poly(good_temps, good_frames, degree):
    x = np.asarray(good_temps, dtype=np.float32)
    frames = np.stack(good_frames, axis=0).astype(np.float32)
    n, h, w = frames.shape
    y = frames.reshape(n, -1)
    vander = np.vander(x, N=degree + 1)
    coeffs, _, _, _ = np.linalg.lstsq(vander, y, rcond=None)
    return coeffs, (h, w)


def _eval_poly(coeffs, shape, temp):
    powers = np.vander([float(temp)], N=coeffs.shape[0])[0].astype(np.float32)
    values = powers @ coeffs
    return values.reshape(shape)


def _quantize_temp(value, places=2):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_target_temps(start_temp, end_temp, step):
    temps = []
    start = _quantize_temp(start_temp)
    end = _quantize_temp(end_temp)
    step = _quantize_temp(step)
    if step <= 0:
        return temps
    current = start
    while current <= end:
        temps.append(float(current))
        current += step
    return temps


def generate_poly_frames(
    entries,
    good_until_temp,
    start_temp,
    end_temp,
    step,
    get_frame_i16,
    degree=3,
    skip_temps=None,
):
    temps = [float(e.temp_value) for e in entries]
    good = [(t, e) for t, e in zip(temps, entries) if t <= good_until_temp]
    if len(good) < degree + 1:
        return {}

    good_temps = [t for t, _ in good]
    good_frames = [get_frame_i16(e).astype(np.float32) for _, e in good]

    target_temps = build_target_temps(start_temp, end_temp, step)
    if not target_temps:
        return {}
    if skip_temps:
        skip_set = {float(_quantize_temp(t)) for t in skip_temps}
    else:
        skip_set = set()

    coeffs, shape = _fit_poly(good_temps, good_frames, degree)
    out = {}
    for t in target_temps:
        if float(_quantize_temp(t)) in skip_set:
            continue
        frame = _eval_poly(coeffs, shape, t)
        out[t] = np.rint(frame).astype(np.int16)
    return out


def make_output_dir(folder):
    parent = os.path.dirname(folder.rstrip("\\/"))
    name = os.path.basename(folder.rstrip("\\/"))
    out_name = f"{name}(gen)"
    out_dir = os.path.join(parent, out_name)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def copy_original_files(src_folder, dst_folder):
    for root, _, files in os.walk(src_folder):
        for name in files:
            if not (name.lower().endswith(".raw") or name.lower().endswith(".txt")):
                continue
            src = os.path.join(root, name)
            rel = os.path.relpath(src, src_folder)
            dst = os.path.join(dst_folder, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def generate_into_folder(
    entries,
    start_temp,
    get_frame_i16,
    output_folder,
    degree=3,
    step=1.25,
    anchor_temp=None,
    end_temp=70.0,
    skip_temps=None,
):
    if not entries:
        return {}
    if anchor_temp is None:
        anchor_temp = start_temp
    generated = generate_poly_frames(
        entries,
        anchor_temp,
        anchor_temp,
        end_temp,
        step,
        get_frame_i16,
        degree=degree,
        skip_temps=skip_temps,
    )
    for temp, frame in generated.items():
        temp_str = f"{temp:.2f}"
        name = f"calib__{temp_str}_{convert_celsius_to_adc(temp)}.raw"
        out_path = os.path.join(output_folder, name)
        write_fpa_image(out_path, frame, temp)
    return generated


def clear_output_dir(folder):
    if not os.path.isdir(folder):
        return
    for root, _, files in os.walk(folder):
        for name in files:
            if name.lower().endswith((".raw", ".txt")):
                os.remove(os.path.join(root, name))


def copy_original_entries(entries, src_root, dst_root, max_temp):
    for entry in entries:
        if float(entry.temp_value) >= max_temp:
            continue
        src_raw = entry.path
        rel = os.path.relpath(src_raw, src_root)
        dst_raw = os.path.join(dst_root, rel)
        os.makedirs(os.path.dirname(dst_raw), exist_ok=True)
        shutil.copy2(src_raw, dst_raw)

        base, _ = os.path.splitext(src_raw)
        src_txt = base + ".txt"
        if os.path.exists(src_txt):
            rel_txt = os.path.relpath(src_txt, src_root)
            dst_txt = os.path.join(dst_root, rel_txt)
            os.makedirs(os.path.dirname(dst_txt), exist_ok=True)
            shutil.copy2(src_txt, dst_txt)
