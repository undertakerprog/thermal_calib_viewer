import os
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import numpy as np

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    QT_API = 'PyQt6'
except ImportError:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets
        QT_API = 'PyQt5'
    except ImportError:
        try:
            from PySide6 import QtCore, QtGui, QtWidgets
            QT_API = 'PySide6'
        except ImportError as exc:
            raise RuntimeError(
                'Missing Qt bindings: install PyQt6 (preferred), PyQt5, or PySide6'
            ) from exc


RAW_PATTERN = re.compile(r'^calib_([+-]?\d+(?:\.\d+)?)_\d+\.raw$', re.IGNORECASE)
DEFAULT_DATA_DIR = os.path.join(os.getcwd(), 'data')
TILE_COLUMNS = 3
PREVIEW_MAX = 240
RAW_WIDTH = 640
RAW_HEIGHT = 480
RAW_HEADER_BYTES = 24

MODE_RAW_LOCAL = 'raw_local'
MODE_RAW_GLOBAL = 'raw_global'
MODE_DIFF_MEAN = 'diff_mean'

MODE_LABELS = {
    MODE_RAW_LOCAL: 'Raw (per-frame scale)',
    MODE_RAW_GLOBAL: 'Raw (global scale)',
    MODE_DIFF_MEAN: 'Diff from triple mean',
}


@dataclass(frozen=True)
class RawEntry:
    temp_value: Decimal
    temp_str: str
    path: str


def scan_raws(root_dir, entries, duplicates):
    if not os.path.isdir(root_dir):
        return duplicates
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            if not name.lower().endswith('.raw'):
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
    return duplicates


def scan_raws_multi(folders):
    entries = {}
    duplicates = 0
    for folder in folders:
        duplicates = scan_raws(folder, entries, duplicates)
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
        raise ValueError(f'Unsupported raw size: {size}')
    width, height, header = dims
    count = width * height
    data = np.fromfile(path, dtype='<u2', count=count, offset=header)
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


def qt_keep_aspect_ratio():
    if hasattr(QtCore.Qt, 'KeepAspectRatio'):
        return QtCore.Qt.KeepAspectRatio
    return QtCore.Qt.AspectRatioMode.KeepAspectRatio


def qt_fast_transform():
    if hasattr(QtCore.Qt, 'FastTransformation'):
        return QtCore.Qt.FastTransformation
    return QtCore.Qt.TransformationMode.FastTransformation


def qt_align_top_left():
    if hasattr(QtCore.Qt, 'AlignTop'):
        return QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
    return QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft


def qt_align_center():
    if hasattr(QtCore.Qt, 'AlignCenter'):
        return QtCore.Qt.AlignCenter
    return QtCore.Qt.AlignmentFlag.AlignCenter


def qimage_format_grayscale8():
    if hasattr(QtGui.QImage, 'Format_Grayscale8'):
        return QtGui.QImage.Format_Grayscale8
    return QtGui.QImage.Format.Format_Grayscale8


def selection_mode_extended():
    if hasattr(QtWidgets.QAbstractItemView, 'ExtendedSelection'):
        return QtWidgets.QAbstractItemView.ExtendedSelection
    return QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection


def selection_mode_none():
    if hasattr(QtWidgets.QAbstractItemView, 'NoSelection'):
        return QtWidgets.QAbstractItemView.NoSelection
    return QtWidgets.QAbstractItemView.SelectionMode.NoSelection


def file_mode_directory():
    if hasattr(QtWidgets.QFileDialog, 'Directory'):
        return QtWidgets.QFileDialog.Directory
    return QtWidgets.QFileDialog.FileMode.Directory


def dialog_option_native():
    if hasattr(QtWidgets.QFileDialog, 'DontUseNativeDialog'):
        return QtWidgets.QFileDialog.DontUseNativeDialog
    return QtWidgets.QFileDialog.Option.DontUseNativeDialog


def dialog_option_show_dirs():
    if hasattr(QtWidgets.QFileDialog, 'ShowDirsOnly'):
        return QtWidgets.QFileDialog.ShowDirsOnly
    return QtWidgets.QFileDialog.Option.ShowDirsOnly


def dialog_exec(dialog):
    if hasattr(dialog, 'exec'):
        return dialog.exec()
    return dialog.exec_()


def dialog_accepted(result):
    if hasattr(QtWidgets.QDialog, 'Accepted'):
        return result == QtWidgets.QDialog.Accepted
    return result == QtWidgets.QDialog.DialogCode.Accepted


def to_qpixmap(frame_u8):
    height, width = frame_u8.shape
    bytes_per_line = width
    image = QtGui.QImage(
        frame_u8.data, width, height, bytes_per_line, qimage_format_grayscale8()
    )
    image = image.copy()
    if max(width, height) > PREVIEW_MAX:
        image = image.scaled(PREVIEW_MAX, PREVIEW_MAX, qt_keep_aspect_ratio(), qt_fast_transform())
    return QtGui.QPixmap.fromImage(image)


class RawModesWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Raw triples viewer (modes)')
        self.resize(1200, 800)
        self.folder_paths = []
        self.entries = []
        self.duplicates = 0
        self.frame_cache = {}
        self.frame_shape = None
        self.pixmap_refs = []
        self.global_scale = None
        self._build_ui()
        if os.path.isdir(DEFAULT_DATA_DIR):
            self.load_folders([DEFAULT_DATA_DIR])

    def _build_ui(self):
        open_action = QtGui.QAction('Open folders...', self)
        open_action.triggered.connect(self.open_folders)
        file_menu = self.menuBar().addMenu('File')
        file_menu.addAction(open_action)

        toolbar = self.addToolBar('Main')
        toolbar.setMovable(False)
        toolbar.addAction(open_action)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.tile_container = QtWidgets.QWidget()
        self.tile_layout = QtWidgets.QGridLayout(self.tile_container)
        self.tile_layout.setContentsMargins(8, 8, 8, 8)
        self.tile_layout.setSpacing(8)
        self.tile_layout.setAlignment(qt_align_top_left())
        self.scroll_area.setWidget(self.tile_container)
        main_layout.addWidget(self.scroll_area, 1)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)

        folder_label = QtWidgets.QLabel('Folders:')
        right_layout.addWidget(folder_label)
        self.folder_list = QtWidgets.QListWidget()
        self.folder_list.setSelectionMode(selection_mode_none())
        right_layout.addWidget(self.folder_list)

        mode_label = QtWidgets.QLabel('Mode:')
        right_layout.addWidget(mode_label)
        self.mode_combo = QtWidgets.QComboBox()
        for key in (MODE_RAW_LOCAL, MODE_RAW_GLOBAL, MODE_DIFF_MEAN):
            self.mode_combo.addItem(MODE_LABELS[key], key)
        right_layout.addWidget(self.mode_combo)

        temp_label = QtWidgets.QLabel('Temperatures:')
        right_layout.addWidget(temp_label)
        self.temp_list = QtWidgets.QListWidget()
        self.temp_list.setSelectionMode(selection_mode_extended())
        right_layout.addWidget(self.temp_list, 1)

        self.update_button = QtWidgets.QPushButton('Update')
        self.update_button.clicked.connect(self.update_tiles)
        right_layout.addWidget(self.update_button)

        self.status_label = QtWidgets.QLabel('')
        right_layout.addWidget(self.status_label)

        main_layout.addWidget(right_panel)

    def open_folders(self):
        dialog = QtWidgets.QFileDialog(self, 'Select folders')
        dialog.setFileMode(file_mode_directory())
        dialog.setOption(dialog_option_native(), True)
        dialog.setOption(dialog_option_show_dirs(), True)
        if self.folder_paths:
            dialog.setDirectory(self.folder_paths[0])
        view = dialog.findChild(QtWidgets.QListView, 'listView')
        if view:
            view.setSelectionMode(selection_mode_extended())
        tree = dialog.findChild(QtWidgets.QTreeView)
        if tree:
            tree.setSelectionMode(selection_mode_extended())
        result = dialog_exec(dialog)
        if dialog_accepted(result):
            folders = dialog.selectedFiles()
            if folders:
                self.load_folders(folders)

    def load_folders(self, folders):
        self.folder_paths = []
        seen = set()
        for folder in folders:
            norm = os.path.normpath(folder)
            if norm in seen:
                continue
            seen.add(norm)
            self.folder_paths.append(norm)
        self.folder_list.clear()
        for folder in self.folder_paths:
            self.folder_list.addItem(folder)

        self.entries, self.duplicates = scan_raws_multi(self.folder_paths)
        self.temp_list.clear()
        for entry in self.entries:
            item = QtWidgets.QListWidgetItem(entry.temp_str)
            self.temp_list.addItem(item)
            item.setSelected(True)

        self.frame_cache.clear()
        self.frame_shape = None
        self.pixmap_refs = []
        self.global_scale = None
        self.update_tiles()

    def get_selected_entries(self):
        indices = sorted(self.temp_list.row(item) for item in self.temp_list.selectedItems())
        return [self.entries[i] for i in indices]

    def get_frame(self, entry):
        if entry.path in self.frame_cache:
            return self.frame_cache[entry.path]
        frame = read_raw_uint16(entry.path)
        if self.frame_shape is None:
            self.frame_shape = frame.shape
        elif frame.shape != self.frame_shape:
            raise ValueError('Mixed raw dimensions are not supported in one view')
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
        mode = self.mode_combo.currentData()
        entry = entries[index]
        frame_i = self.get_frame(entry)
        frame_j = self.get_frame(entries[index + 1])
        frame_k = self.get_frame(entries[index + 2])

        if mode == MODE_RAW_LOCAL:
            frame_u8 = scale_uint16_to_uint8(frame_i)
        elif mode == MODE_RAW_GLOBAL:
            p1, p99 = self.compute_global_scale(entries)
            frame_u8 = scale_uint16_to_uint8(frame_i, p1, p99)
        elif mode == MODE_DIFF_MEAN:
            mean = (frame_i.astype(np.float32) + frame_j.astype(np.float32) + frame_k.astype(np.float32)) / 3.0
            diff = frame_i.astype(np.float32) - mean
            frame_u8 = scale_diff_signed(diff)
        else:
            frame_u8 = scale_uint16_to_uint8(frame_i)

        return to_qpixmap(frame_u8)

    def clear_tiles(self):
        while self.tile_layout.count():
            item = self.tile_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def update_tiles(self):
        self.clear_tiles()
        self.pixmap_refs = []
        self.global_scale = None

        selected = self.get_selected_entries()
        tiles = max(0, len(selected) - 2)
        if tiles == 0:
            status = f'Raw files: {len(self.entries)} | selected: {len(selected)} | tiles: 0'
            if self.duplicates:
                status += f' | duplicates ignored: {self.duplicates}'
            self.status_label.setText(status)
            return

        for i in range(tiles):
            label_text = (
                f'{selected[i].temp_str} | {selected[i + 1].temp_str} | {selected[i + 2].temp_str}'
            )
            tile = QtWidgets.QFrame()
            if hasattr(QtWidgets.QFrame, 'Box'):
                tile.setFrameShape(QtWidgets.QFrame.Box)
            else:
                tile.setFrameShape(QtWidgets.QFrame.Shape.Box)
            tile_layout = QtWidgets.QVBoxLayout(tile)
            tile_layout.setContentsMargins(4, 4, 4, 4)

            try:
                pixmap = self.render_tile(selected, i)
                image_label = QtWidgets.QLabel()
                image_label.setAlignment(qt_align_center())
                image_label.setPixmap(pixmap)
                tile_layout.addWidget(image_label)
                self.pixmap_refs.append(pixmap)
            except Exception as exc:
                error_label = QtWidgets.QLabel(f'Preview error: {exc}')
                tile_layout.addWidget(error_label)

            caption = QtWidgets.QLabel(label_text)
            caption.setAlignment(qt_align_center())
            tile_layout.addWidget(caption)

            self.tile_layout.addWidget(tile, i // TILE_COLUMNS, i % TILE_COLUMNS)

        status = f'Raw files: {len(self.entries)} | selected: {len(selected)} | tiles: {tiles}'
        mode_label = MODE_LABELS.get(self.mode_combo.currentData(), self.mode_combo.currentText())
        status += f' | mode: {mode_label}'
        if self.duplicates:
            status += f' | duplicates ignored: {self.duplicates}'
        self.status_label.setText(status)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = RawModesWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
