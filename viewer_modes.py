import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import filedialog, ttk

import numpy as np
from PIL import Image, ImageTk


RAW_PATTERN = re.compile(r"^calib_([+-]?\d+(?:\.\d+)?)_\d+\.raw$", re.IGNORECASE)
DEFAULT_DATA_DIR = os.path.join(os.getcwd(), "data")
TILE_COLUMNS = 3
PREVIEW_MAX = 240
RAW_WIDTH = 640
RAW_HEIGHT = 480
RAW_HEADER_BYTES = 24

MODE_RAW_LOCAL = "raw_local"
MODE_RAW_GLOBAL = "raw_global"
MODE_DIFF_NEXT = "diff_next"
MODE_DIFF_NEXT_ABS = "diff_next_abs"
MODE_DIFF_MEAN = "diff_mean"

MODE_LABELS = {
    MODE_RAW_LOCAL: "Raw (per-frame scale)",
    MODE_RAW_GLOBAL: "Raw (global scale)",
    MODE_DIFF_NEXT: "Diff next (signed)",
    MODE_DIFF_NEXT_ABS: "Diff next (abs)",
    MODE_DIFF_MEAN: "Diff from triple mean",
}


@dataclass(frozen=True)
class RawEntry:
    temp_value: Decimal
    temp_str: str
    path: str


def scan_raws(root_dir):
    entries = {}
    duplicates = 0
    if not os.path.isdir(root_dir):
        return [], duplicates
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if not name.lower().endswith(".raw"):
                continue
            match = RAW_PATTERN.match(name)
            if not match:
                continue
            temp_str = match.group(1)
            try:
                temp_value = Decimal(temp_str)
            except InvalidOperation:
                continue
            path = os.path.join(dirpath, name)
            if temp_value in entries:
                duplicates += 1
                if path < entries[temp_value].path:
                    entries[temp_value] = RawEntry(temp_value, temp_str, path)
                continue
            entries[temp_value] = RawEntry(temp_value, temp_str, path)
    ordered = [entries[key] for key in sorted(entries.keys())]
    return ordered, duplicates


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


def read_raw_uint16(path):
    size = os.path.getsize(path)
    dims = guess_dimensions(size)
    if not dims:
        raise ValueError(f"Unsupported raw size: {size}")
    width, height, header = dims
    count = width * height
    data = np.fromfile(path, dtype="<u2", count=count, offset=header)
    if data.size < count:
        raise ValueError("Raw file is too small for expected dimensions")
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


def to_photo_image(frame_u8):
    image = Image.fromarray(frame_u8, mode="L")
    image.thumbnail((PREVIEW_MAX, PREVIEW_MAX), Image.NEAREST)
    return ImageTk.PhotoImage(image)


class RawModesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Raw triples viewer (modes)")
        self.current_folder = DEFAULT_DATA_DIR
        self.entries = []
        self.duplicates = 0
        self.frame_cache = {}
        self.frame_shape = None
        self.image_cache = {}
        self.photo_refs = []
        self.global_scale = None
        self._build_ui()
        self.load_folder(self.current_folder)

    def _build_ui(self):
        self.root.geometry("1200x800")
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(main)
        right.pack(side="right", fill="y")

        self.tile_canvas = tk.Canvas(left, borderwidth=0, highlightthickness=0)
        self.tile_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tile_canvas.yview)
        self.tile_canvas.configure(yscrollcommand=self.tile_scroll.set)
        self.tile_scroll.pack(side="right", fill="y")
        self.tile_canvas.pack(side="left", fill="both", expand=True)

        self.tile_inner = ttk.Frame(self.tile_canvas)
        self.tile_canvas_window = self.tile_canvas.create_window(
            (0, 0), window=self.tile_inner, anchor="nw"
        )
        self.tile_inner.bind("<Configure>", self._on_tile_inner_configure)
        self.tile_canvas.bind("<Configure>", self._on_tile_canvas_configure)

        folder_label = ttk.Label(right, text="Folder:")
        folder_label.pack(anchor="w")
        self.folder_value = ttk.Label(right, text="", wraplength=260)
        self.folder_value.pack(anchor="w", pady=(0, 6))

        choose_button = ttk.Button(right, text="Choose folder", command=self.choose_folder)
        choose_button.pack(fill="x", pady=(0, 8))

        mode_label = ttk.Label(right, text="Mode:")
        mode_label.pack(anchor="w")
        self.mode_var = tk.StringVar(value=MODE_RAW_LOCAL)
        self.mode_combo = ttk.Combobox(
            right,
            textvariable=self.mode_var,
            values=[MODE_RAW_LOCAL, MODE_RAW_GLOBAL, MODE_DIFF_NEXT, MODE_DIFF_NEXT_ABS, MODE_DIFF_MEAN],
            state="readonly",
        )
        self.mode_combo.pack(fill="x", pady=(0, 8))

        list_label = ttk.Label(right, text="Temperatures:")
        list_label.pack(anchor="w")
        list_frame = ttk.Frame(right)
        list_frame.pack(fill="both", expand=True)

        self.temp_list = tk.Listbox(list_frame, selectmode="extended", exportselection=False)
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.temp_list.yview)
        self.temp_list.configure(yscrollcommand=list_scroll.set)
        self.temp_list.pack(side="left", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y")

        update_button = ttk.Button(right, text="Update", command=self.update_tiles)
        update_button.pack(fill="x", pady=(8, 4))

        self.status_label = ttk.Label(right, text="")
        self.status_label.pack(anchor="w")

    def _on_tile_inner_configure(self, _event):
        self.tile_canvas.configure(scrollregion=self.tile_canvas.bbox("all"))

    def _on_tile_canvas_configure(self, event):
        self.tile_canvas.itemconfigure(self.tile_canvas_window, width=event.width)

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_folder or os.getcwd())
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder):
        self.current_folder = folder
        self.folder_value.config(text=self.current_folder)
        self.entries, self.duplicates = scan_raws(folder)
        self.temp_list.delete(0, tk.END)
        for entry in self.entries:
            self.temp_list.insert(tk.END, entry.temp_str)
        if self.entries:
            self.temp_list.select_set(0, tk.END)
        self.frame_cache.clear()
        self.frame_shape = None
        self.image_cache.clear()
        self.global_scale = None
        self.update_tiles()

    def get_selected_entries(self):
        indices = self.temp_list.curselection()
        return [self.entries[i] for i in indices]

    def get_frame(self, entry):
        if entry.path in self.frame_cache:
            return self.frame_cache[entry.path]
        frame = read_raw_uint16(entry.path)
        if self.frame_shape is None:
            self.frame_shape = frame.shape
        elif frame.shape != self.frame_shape:
            raise ValueError("Mixed raw dimensions are not supported in one view")
        self.frame_cache[entry.path] = frame
        return frame

    def compute_global_scale(self, entries):
        if self.global_scale is not None:
            return self.global_scale
        samples = []
        for entry in entries:
            frame = self.get_frame(entry)
            samples.append(frame[::8, ::8].ravel())
        merged = np.concatenate(samples)
        p1 = np.percentile(merged, 1)
        p99 = np.percentile(merged, 99)
        if p99 <= p1:
            p99 = p1 + 1
        self.global_scale = (p1, p99)
        return self.global_scale

    def render_tile(self, entries, index):
        mode = self.mode_var.get()
        entry = entries[index]
        frame_i = self.get_frame(entry)
        frame_j = self.get_frame(entries[index + 1])
        frame_k = self.get_frame(entries[index + 2])

        if mode == MODE_RAW_LOCAL:
            frame_u8 = scale_uint16_to_uint8(frame_i)
        elif mode == MODE_RAW_GLOBAL:
            p1, p99 = self.compute_global_scale(entries)
            frame_u8 = scale_uint16_to_uint8(frame_i, p1, p99)
        elif mode == MODE_DIFF_NEXT:
            diff = frame_i.astype(np.int32) - frame_j.astype(np.int32)
            frame_u8 = scale_diff_signed(diff)
        elif mode == MODE_DIFF_NEXT_ABS:
            diff = np.abs(frame_i.astype(np.int32) - frame_j.astype(np.int32))
            frame_u8 = scale_uint16_to_uint8(diff)
        elif mode == MODE_DIFF_MEAN:
            mean = (frame_i.astype(np.float32) + frame_j.astype(np.float32) + frame_k.astype(np.float32)) / 3.0
            diff = frame_i.astype(np.float32) - mean
            frame_u8 = scale_diff_signed(diff)
        else:
            frame_u8 = scale_uint16_to_uint8(frame_i)

        return to_photo_image(frame_u8)

    def update_tiles(self):
        for widget in self.tile_inner.winfo_children():
            widget.destroy()
        self.photo_refs = []
        self.image_cache.clear()
        self.global_scale = None

        selected = self.get_selected_entries()
        tiles = max(0, len(selected) - 2)
        if tiles == 0:
            status = f"Raw files: {len(self.entries)} | selected: {len(selected)} | tiles: 0"
            if self.duplicates:
                status += f" | duplicates ignored: {self.duplicates}"
            self.status_label.config(text=status)
            return

        for i in range(tiles):
            label_text = f"{selected[i].temp_str} | {selected[i + 1].temp_str} | {selected[i + 2].temp_str}"
            tile = ttk.Frame(self.tile_inner, padding=4, relief="solid")
            tile.grid(row=i // TILE_COLUMNS, column=i % TILE_COLUMNS, padx=4, pady=4, sticky="n")
            try:
                photo = self.render_tile(selected, i)
                image_label = ttk.Label(tile, image=photo)
                image_label.pack()
                self.photo_refs.append(photo)
            except Exception as exc:
                error_label = ttk.Label(tile, text=f"Preview error: {exc}")
                error_label.pack()
            caption = ttk.Label(tile, text=label_text)
            caption.pack()

        status = f"Raw files: {len(self.entries)} | selected: {len(selected)} | tiles: {tiles}"
        status += f" | mode: {MODE_LABELS.get(self.mode_var.get(), self.mode_var.get())}"
        if self.duplicates:
            status += f" | duplicates ignored: {self.duplicates}"
        self.status_label.config(text=status)


def main():
    root = tk.Tk()
    app = RawModesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
