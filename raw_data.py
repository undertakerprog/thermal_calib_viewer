import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import numpy as np


RAW_PATTERN = re.compile(r'^calib_+([+-]?\d+(?:\.\d+)?)_(\d+)\.raw$', re.IGNORECASE)
RAW_WIDTH = 640
RAW_HEIGHT = 480
RAW_HEADER_BYTES = 24
MAT_HEADER_BYTES = 24


@dataclass(frozen=True)
class RawEntry:
    temp_value: Decimal
    temp_str: str
    adc_value: int
    adc_str: str
    path: str


def scan_raws(root_dir):
    entries = []
    temp_counts = {}
    duplicates = 0
    if not os.path.isdir(root_dir):
        return [], duplicates
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if not name.lower().endswith('.raw'):
                continue
            match = RAW_PATTERN.match(name)
            if not match:
                continue
            temp_str = match.group(1)
            adc_str = match.group(2)
            try:
                temp_value = Decimal(temp_str)
            except InvalidOperation:
                continue
            try:
                adc_value = int(adc_str)
            except ValueError:
                adc_value = 0
            path = os.path.join(dirpath, name)
            temp_counts[temp_value] = temp_counts.get(temp_value, 0) + 1
            entries.append(RawEntry(temp_value, temp_str, adc_value, adc_str, path))
    duplicates = sum(count - 1 for count in temp_counts.values() if count > 1)
    entries.sort(key=lambda entry: (entry.temp_value, entry.adc_value, entry.path))
    return entries, duplicates


def guess_dimensions(file_size):
    if file_size == RAW_WIDTH * RAW_HEIGHT * 2 + RAW_HEADER_BYTES:
        return RAW_WIDTH, RAW_HEIGHT, RAW_HEADER_BYTES
    if file_size == RAW_WIDTH * RAW_HEIGHT * 2:
        return RAW_WIDTH, RAW_HEIGHT, 0
    header_sizes = [0, 24, 32, 64, 128]
    common_dims = [
        (640, 480),
        (512, 512),
        (512, 384),
        (384, 288),
        (320, 240),
        (800, 600),
        (1024, 768),
        (1280, 1024),
    ]
    common_widths = [640, 512, 384, 320, 800, 1024, 1280, 480, 720, 960, 1920]
    for header in header_sizes:
        payload = file_size - header
        if payload <= 0 or payload % 2 != 0:
            continue
        pixels = payload // 2
        for width, height in common_dims:
            if width * height == pixels:
                return width, height, header
        for width in common_widths:
            if pixels % width == 0:
                height = pixels // width
                if 1 < height <= 4096:
                    return width, height, header
    return None


def _read_mat_header(path):
    size = os.path.getsize(path)
    if size < MAT_HEADER_BYTES:
        return None
    with open(path, "rb") as handle:
        header = handle.read(MAT_HEADER_BYTES)
    if len(header) != MAT_HEADER_BYTES:
        return None
    t_adc = np.frombuffer(header[:4], dtype="<f4")[0]
    cols = np.frombuffer(header[4:8], dtype="<i4")[0]
    rows = np.frombuffer(header[8:12], dtype="<i4")[0]
    mat_type = np.frombuffer(header[12:16], dtype="<i4")[0]
    data_size = np.frombuffer(header[16:24], dtype="<u8")[0]
    if cols <= 0 or rows <= 0:
        return None
    expected = cols * rows * 2
    if mat_type != 3 or data_size != expected:
        return None
    if MAT_HEADER_BYTES + data_size > size:
        return None
    return cols, rows, MAT_HEADER_BYTES


def read_raw_uint16(path):
    size = os.path.getsize(path)
    dims = _read_mat_header(path)
    if not dims:
        dims = guess_dimensions(size)
    if not dims:
        raise ValueError(f'Unsupported raw size: {size}')
    width, height, header = dims
    count = width * height
    data = np.fromfile(path, dtype='<u2', count=count, offset=header)
    if data.size < count:
        raise ValueError('Raw file is too small for expected dimensions')
    return data.reshape((height, width))


def read_raw_int16(path):
    size = os.path.getsize(path)
    dims = _read_mat_header(path)
    if not dims:
        dims = guess_dimensions(size)
    if not dims:
        raise ValueError(f'Unsupported raw size: {size}')
    width, height, header = dims
    count = width * height
    data = np.fromfile(path, dtype='<i2', count=count, offset=header)
    if data.size < count:
        raise ValueError('Raw file is too small for expected dimensions')
    return data.reshape((height, width))


def scale_uint16_to_uint8(frame, p1=None, p99=None):
    if p1 is None or p99 is None:
        p1 = np.percentile(frame, 1)
        p99 = np.percentile(frame, 99)
    if p99 <= p1:
        p99 = p1 + 1
    frame = np.clip(frame, p1, p99)
    scaled = ((frame - p1) * (255.0 / (p99 - p1))).astype(np.uint8)
    return scaled


def scale_diff_signed(diff):
    p1 = np.percentile(diff, 1)
    p99 = np.percentile(diff, 99)
    max_abs = max(abs(p1), abs(p99), 1.0)
    scaled = (diff / max_abs) * 127.0 + 128.0
    return np.clip(scaled, 0, 255).astype(np.uint8)
