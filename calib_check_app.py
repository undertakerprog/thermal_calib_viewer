import os
import sys

import qt_compat as qt
from raw_data import read_raw_int16, scan_raws
from std_calib import std_calib_lhe
from calib_detect import detect_bad


DEFAULT_DATA_DIR = os.path.join(os.getcwd(), 'data')
TILE_COLUMNS = 3
PREVIEW_MAX = 240


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


class CalibCheckWindow(qt.QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('StdCalib check')
        self.resize(1200, 800)
        self.entries = []
        self.duplicates = 0
        self.frame_cache_i16 = {}
        self.frame_shape = None
        self.pixmap_refs = []
        self.current_folder = None
        self._build_ui()
        if os.path.isdir(DEFAULT_DATA_DIR):
            self.load_folder(DEFAULT_DATA_DIR)

    def _build_ui(self):
        central = qt.QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = qt.QtWidgets.QHBoxLayout(central)

        left_panel = qt.QtWidgets.QWidget()
        left_layout = qt.QtWidgets.QVBoxLayout(left_panel)

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

        self.open_button = qt.QtWidgets.QPushButton('Open folder...')
        self.open_button.clicked.connect(self.open_folder)
        right_layout.addWidget(self.open_button)

        current_label = qt.QtWidgets.QLabel('Current folder:')
        right_layout.addWidget(current_label)
        self.current_folder_label = qt.QtWidgets.QLabel('')
        self.current_folder_label.setWordWrap(True)
        right_layout.addWidget(self.current_folder_label)

        temp_label = qt.QtWidgets.QLabel('Temperatures:')
        right_layout.addWidget(temp_label)
        self.temp_list = qt.QtWidgets.QListWidget()
        self.temp_list.setSelectionMode(qt.selection_mode_extended())
        right_layout.addWidget(self.temp_list, 1)

        self.update_button = qt.QtWidgets.QPushButton('Update')
        self.update_button.clicked.connect(self.refresh_current)
        right_layout.addWidget(self.update_button)

        self.detect_button = qt.QtWidgets.QPushButton('Detect first bad')
        self.detect_button.clicked.connect(self.detect_first_bad)
        right_layout.addWidget(self.detect_button)

        self.detect_label = qt.QtWidgets.QLabel('Detection: not run')
        self.detect_label.setWordWrap(True)
        right_layout.addWidget(self.detect_label)

        self.status_label = qt.QtWidgets.QLabel('')
        right_layout.addWidget(self.status_label)

        main_layout.addWidget(right_panel)

    def open_folder(self):
        dialog = qt.QtWidgets.QFileDialog(self, 'Select folder')
        dialog.setFileMode(qt.file_mode_directory())
        dialog.setOption(qt.dialog_option_native(), True)
        dialog.setOption(qt.dialog_option_show_dirs(), True)
        if self.current_folder:
            dialog.setDirectory(self.current_folder)
        result = qt.dialog_exec(dialog)
        if qt.dialog_accepted(result):
            folders = dialog.selectedFiles()
            if folders:
                self.load_folder(folders[0])

    def load_folder(self, folder):
        self.current_folder = folder
        self.current_folder_label.setText(folder)
        self.entries, self.duplicates = scan_raws(folder)
        self.temp_list.clear()
        for entry in self.entries:
            item = qt.QtWidgets.QListWidgetItem(entry.temp_str)
            self.temp_list.addItem(item)
            item.setSelected(True)
        self.frame_cache_i16.clear()
        self.frame_shape = None
        self.pixmap_refs = []
        self.detect_label.setText('Detection: not run')
        self.update_tiles()

    def refresh_current(self):
        if self.current_folder:
            self.load_folder(self.current_folder)

    def get_selected_entries(self):
        indices = sorted(self.temp_list.row(item) for item in self.temp_list.selectedItems())
        return [self.entries[i] for i in indices]

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

    def render_tile(self, entries, index):
        entry_prev = entries[index]
        entry_curr = entries[index + 1]
        entry_next = entries[index + 2]
        frame_u8 = std_calib_lhe(
            self.get_frame_i16(entry_prev),
            self.get_frame_i16(entry_curr),
            self.get_frame_i16(entry_next),
            entry_prev.temp_value,
            entry_curr.temp_value,
            entry_next.temp_value,
        )
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
        if self.duplicates:
            status += f' | duplicate temps: {self.duplicates}'
        self.status_label.setText(status)

    def detect_first_bad(self):
        selected = self.get_selected_entries()
        if len(selected) < 3:
            self.detect_label.setText('Detection: not enough frames')
            return
        result = detect_bad(selected, self.get_frame_i16)
        outliers = result.get("outliers") or []
        if outliers:
            outlier_text = ", ".join(entry.temp_str for entry in outliers)
        else:
            outlier_text = ""

        if result["bad_idx"] is None:
            if result.get("threshold") is None:
                text = 'Detection: not enough data'
            else:
                text = (
                    f'Detection: no bad frames '
                    f'(threshold {result["threshold"]:.2f}, baseline {result["baseline"]:.2f})'
                )
            if outlier_text:
                text += f' | temp outliers: {outlier_text}'
            self.detect_label.setText(text)
            return

        bad_idx = result["bad_idx"]
        bad_entry = result["bad_entry"]
        triple = (
            f'{selected[bad_idx].temp_str} | '
            f'{selected[bad_idx + 1].temp_str} | '
            f'{selected[bad_idx + 2].temp_str}'
        )
        reason = result.get("reason", "detected")
        score = result.get("score")
        threshold = result.get("threshold")
        text = f'Detection: bad from {bad_entry.temp_str} ({reason})'
        if score is not None and threshold is not None:
            text += f' | score {score:.2f} > {threshold:.2f}'
        text += f' | triple {triple}'
        if outlier_text:
            text += f' | temp outliers: {outlier_text}'
        self.detect_label.setText(text)


def main():
    app = qt.QtWidgets.QApplication(sys.argv)
    qt.apply_light_theme(app)
    window = CalibCheckWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
