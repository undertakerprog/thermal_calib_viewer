import os
import sys

import numpy as np

import qt_compat as qt
from raw_data import read_raw_int16, read_raw_uint16, scan_raws, scale_diff_signed, scale_uint16_to_uint8
from std_calib import std_calib_lhe


DEFAULT_DATA_DIR = os.path.join(os.getcwd(), 'data')
TILE_COLUMNS = 3
PREVIEW_MAX = 240

MODE_RAW_LOCAL = 'raw_local'
MODE_RAW_GLOBAL = 'raw_global'
MODE_DIFF_MEAN = 'diff_mean'
MODE_CALIB_INTERP = 'calib_interp'

MODE_LABELS = {
    MODE_RAW_LOCAL: 'Raw (per-frame scale)',
    MODE_RAW_GLOBAL: 'Raw (global scale)',
    MODE_DIFF_MEAN: 'Diff from triple mean',
    MODE_CALIB_INTERP: 'StdCalib (LHE)',
}


def to_qpixmap(frame_u8):
    height, width = frame_u8.shape
    bytes_per_line = width
    image = qt.QtGui.QImage(
        frame_u8.data, width, height, bytes_per_line, qt.qimage_format_grayscale8()
    )
    image = image.copy()
    if max(width, height) > PREVIEW_MAX:
        image = image.scaled(PREVIEW_MAX, PREVIEW_MAX, qt.keep_aspect_ratio(), qt.fast_transform())
    return qt.QtGui.QPixmap.fromImage(image)


class RawModesWindow(qt.QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Raw triples viewer (modes)')
        self.resize(1200, 800)
        self.entries = []
        self.duplicates = 0
        self.frame_cache = {}
        self.frame_cache_i16 = {}
        self.frame_shape = None
        self.pixmap_refs = []
        self.global_scale = None
        self.current_folder = None
        self._build_ui()
        if os.path.isdir(DEFAULT_DATA_DIR):
            self.add_folders([DEFAULT_DATA_DIR])

    def _build_ui(self):
        central = qt.QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = qt.QtWidgets.QHBoxLayout(central)

        left_panel = qt.QtWidgets.QWidget()
        left_layout = qt.QtWidgets.QVBoxLayout(left_panel)

        self.folder_tabs = qt.QtWidgets.QTabBar()
        self.folder_tabs.setMovable(True)
        self.folder_tabs.setTabsClosable(True)
        self.folder_tabs.currentChanged.connect(self.on_tab_changed)
        self.folder_tabs.tabCloseRequested.connect(self.close_tab)
        left_layout.addWidget(self.folder_tabs)

        self.scroll_area = qt.QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.tile_container = qt.QtWidgets.QWidget()
        self.tile_layout = qt.QtWidgets.QGridLayout(self.tile_container)
        self.tile_layout.setContentsMargins(8, 8, 8, 8)
        self.tile_layout.setSpacing(8)
        self.tile_layout.setAlignment(qt.align_top_left())
        self.scroll_area.setWidget(self.tile_container)
        left_layout.addWidget(self.scroll_area, 1)

        main_layout.addWidget(left_panel, 1)

        right_panel = qt.QtWidgets.QWidget()
        right_layout = qt.QtWidgets.QVBoxLayout(right_panel)

        self.add_button = qt.QtWidgets.QPushButton('Add folders...')
        self.add_button.clicked.connect(self.open_folders)
        right_layout.addWidget(self.add_button)

        current_label = qt.QtWidgets.QLabel('Current folder:')
        right_layout.addWidget(current_label)
        self.current_folder_label = qt.QtWidgets.QLabel('')
        self.current_folder_label.setWordWrap(True)
        right_layout.addWidget(self.current_folder_label)

        mode_label = qt.QtWidgets.QLabel('Mode:')
        right_layout.addWidget(mode_label)
        self.mode_combo = qt.QtWidgets.QComboBox()
        for key in (MODE_RAW_LOCAL, MODE_RAW_GLOBAL, MODE_DIFF_MEAN):
            self.mode_combo.addItem(MODE_LABELS[key], key)
        self.mode_combo.addItem(MODE_LABELS[MODE_CALIB_INTERP], MODE_CALIB_INTERP)
        right_layout.addWidget(self.mode_combo)

        temp_label = qt.QtWidgets.QLabel('Temperatures:')
        right_layout.addWidget(temp_label)
        self.temp_list = qt.QtWidgets.QListWidget()
        self.temp_list.setSelectionMode(qt.selection_mode_extended())
        right_layout.addWidget(self.temp_list, 1)

        self.update_button = qt.QtWidgets.QPushButton('Update')
        self.update_button.clicked.connect(self.refresh_current)
        right_layout.addWidget(self.update_button)

        self.status_label = qt.QtWidgets.QLabel('')
        right_layout.addWidget(self.status_label)

        main_layout.addWidget(right_panel)

    def make_tab_title(self, folder):
        base = os.path.basename(os.path.normpath(folder)) or folder
        existing = {self.folder_tabs.tabText(i) for i in range(self.folder_tabs.count())}
        if base not in existing:
            return base
        index = 2
        while f'{base} ({index})' in existing:
            index += 1
        return f'{base} ({index})'

    def add_folders(self, folders):
        added_index = None
        seen = {self.folder_tabs.tabData(i) for i in range(self.folder_tabs.count())}
        for folder in folders:
            norm = os.path.normpath(folder)
            if norm in seen:
                continue
            seen.add(norm)
            title = self.make_tab_title(norm)
            index = self.folder_tabs.addTab(title)
            self.folder_tabs.setTabToolTip(index, norm)
            self.folder_tabs.setTabData(index, norm)
            if added_index is None:
                added_index = index
        if added_index is not None:
            self.folder_tabs.setCurrentIndex(added_index)

    def open_folders(self):
        dialog = qt.QtWidgets.QFileDialog(self, 'Select folders')
        dialog.setFileMode(qt.file_mode_directory())
        dialog.setOption(qt.dialog_option_native(), True)
        dialog.setOption(qt.dialog_option_show_dirs(), True)
        if self.current_folder:
            dialog.setDirectory(self.current_folder)
        view = dialog.findChild(qt.QtWidgets.QListView, 'listView')
        if view:
            view.setSelectionMode(qt.selection_mode_extended())
        tree = dialog.findChild(qt.QtWidgets.QTreeView)
        if tree:
            tree.setSelectionMode(qt.selection_mode_extended())
        result = qt.dialog_exec(dialog)
        if qt.dialog_accepted(result):
            folders = dialog.selectedFiles()
            if folders:
                self.add_folders(folders)

    def on_tab_changed(self, index):
        path = self.folder_tabs.tabData(index) if index >= 0 else None
        if path:
            self.load_folder(path)
        else:
            self.clear_view()

    def close_tab(self, index):
        self.folder_tabs.removeTab(index)
        if self.folder_tabs.count() == 0:
            self.clear_view()
        elif self.folder_tabs.currentIndex() == -1:
            self.folder_tabs.setCurrentIndex(0)

    def load_folder(self, folder):
        self.current_folder = folder
        self.current_folder_label.setText(folder)
        self.entries, self.duplicates = scan_raws(folder)
        self.temp_list.clear()
        for entry in self.entries:
            item = qt.QtWidgets.QListWidgetItem(entry.temp_str)
            self.temp_list.addItem(item)
            item.setSelected(True)
        self.frame_cache.clear()
        self.frame_cache_i16.clear()
        self.frame_shape = None
        self.pixmap_refs = []
        self.global_scale = None
        self.update_tiles()

    def refresh_current(self):
        if self.current_folder:
            self.load_folder(self.current_folder)

    def clear_view(self):
        self.current_folder = None
        self.current_folder_label.setText('')
        self.entries = []
        self.duplicates = 0
        self.temp_list.clear()
        self.frame_cache.clear()
        self.frame_cache_i16.clear()
        self.frame_shape = None
        self.pixmap_refs = []
        self.global_scale = None
        self.clear_tiles()
        self.status_label.setText('No folders opened.')

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

    def get_frame_i16(self, entry):
        if entry.path in self.frame_cache_i16:
            return self.frame_cache_i16[entry.path]
        frame = read_raw_int16(entry.path)
        if self.frame_shape is None:
            self.frame_shape = frame.shape
        elif frame.shape != self.frame_shape:
            raise ValueError('Mixed raw dimensions are not supported in one view')
        self.frame_cache_i16[entry.path] = frame
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
        entry_prev = entries[index]
        entry_curr = entries[index + 1]
        entry_next = entries[index + 2]
        frame_i = self.get_frame(entry_prev)
        frame_j = self.get_frame(entry_curr)
        frame_k = self.get_frame(entry_next)

        if mode == MODE_RAW_LOCAL:
            frame_u8 = scale_uint16_to_uint8(frame_i)
        elif mode == MODE_RAW_GLOBAL:
            p1, p99 = self.compute_global_scale(entries)
            frame_u8 = scale_uint16_to_uint8(frame_i, p1, p99)
        elif mode == MODE_DIFF_MEAN:
            mean = (frame_i.astype(np.float32) + frame_j.astype(np.float32) + frame_k.astype(np.float32)) / 3.0
            diff = frame_i.astype(np.float32) - mean
            frame_u8 = scale_diff_signed(diff)
        elif mode == MODE_CALIB_INTERP:
            frame_prev = self.get_frame_i16(entry_prev)
            frame_curr = self.get_frame_i16(entry_curr)
            frame_next = self.get_frame_i16(entry_next)
            frame_u8 = std_calib_lhe(
                frame_prev,
                frame_curr,
                frame_next,
                entry_prev.temp_value,
                entry_curr.temp_value,
                entry_next.temp_value,
            )
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
                status += f' | duplicate temps: {self.duplicates}'
            self.status_label.setText(status)
            return

        for i in range(tiles):
            label_text = (
                f'{selected[i].temp_str} | {selected[i + 1].temp_str} | {selected[i + 2].temp_str}'
            )
            tile = qt.QtWidgets.QFrame()
            if hasattr(qt.QtWidgets.QFrame, 'Box'):
                tile.setFrameShape(qt.QtWidgets.QFrame.Box)
            else:
                tile.setFrameShape(qt.QtWidgets.QFrame.Shape.Box)
            tile_layout = qt.QtWidgets.QVBoxLayout(tile)
            tile_layout.setContentsMargins(4, 4, 4, 4)

            try:
                pixmap = self.render_tile(selected, i)
                image_label = qt.QtWidgets.QLabel()
                image_label.setAlignment(qt.align_center())
                image_label.setPixmap(pixmap)
                tile_layout.addWidget(image_label)
                self.pixmap_refs.append(pixmap)
            except Exception as exc:
                error_label = qt.QtWidgets.QLabel(f'Preview error: {exc}')
                tile_layout.addWidget(error_label)

            caption = qt.QtWidgets.QLabel(label_text)
            caption.setAlignment(qt.align_center())
            tile_layout.addWidget(caption)

            self.tile_layout.addWidget(tile, i // TILE_COLUMNS, i % TILE_COLUMNS)

        status = f'Raw files: {len(self.entries)} | selected: {len(selected)} | tiles: {tiles}'
        mode_label = MODE_LABELS.get(self.mode_combo.currentData(), self.mode_combo.currentText())
        status += f' | mode: {mode_label}'
        if self.duplicates:
            status += f' | duplicate temps: {self.duplicates}'
        self.status_label.setText(status)


def main():
    app = qt.QtWidgets.QApplication(sys.argv)
    window = RawModesWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
