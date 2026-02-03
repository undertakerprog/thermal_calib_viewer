import math
import os
import sys

import numpy as np

import qt_compat as qt
from calib_detect import detect_bad
from calib_generate import (
    clear_output_dir,
    copy_original_entries,
    generate_into_folder,
    make_output_dir,
)
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


def palette_role(name):
    if hasattr(qt.QtGui.QPalette, name):
        return getattr(qt.QtGui.QPalette, name)
    return getattr(qt.QtGui.QPalette.ColorRole, name)


class TemperaturePlot(qt.QtWidgets.QWidget):
    def __init__(self, show_points=True, point_radius=3, show_labels=True):
        super().__init__()
        self._temps = []
        self._show_points = show_points
        self._point_radius = point_radius
        self._show_labels = show_labels
        self.setMinimumHeight(260)

    def set_temperatures(self, temps):
        self._temps = [float(value) for value in temps]
        self.update()

    def set_show_points(self, value):
        self._show_points = bool(value)
        self.update()

    def set_point_radius(self, value):
        self._point_radius = max(0, int(value))
        self.update()

    def set_show_labels(self, value):
        self._show_labels = bool(value)
        self.update()

    def paintEvent(self, event):
        painter = qt.QtGui.QPainter(self)
        painter.setRenderHint(qt.QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        base_color = self.palette().color(palette_role('Base'))
        text_color = self.palette().color(palette_role('Text'))
        painter.fillRect(rect, base_color)

        if not self._temps:
            painter.setPen(text_color)
            painter.drawText(rect, qt.align_center(), 'No data')
            return

        left = 64
        right = 12
        top = 12
        bottom = 36
        plot_rect = rect.adjusted(left, top, -right, -bottom)
        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return

        temps = self._temps
        count = len(temps)
        x_min = 1.0
        x_max = float(count)
        y_min = float(min(temps))
        y_max = float(max(temps))
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0
        y_pad = max((y_max - y_min) * 0.05, 1.0)
        y_min -= y_pad
        y_max += y_pad

        def x_pos(index):
            span = x_max - x_min or 1.0
            return plot_rect.left() + (index - x_min) / span * plot_rect.width()

        def y_pos(value):
            span = y_max - y_min or 1.0
            return plot_rect.bottom() - (value - y_min) / span * plot_rect.height()

        axis_pen = qt.QtGui.QPen(text_color)
        painter.setPen(axis_pen)
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.bottomRight())
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.topLeft())

        tick_count = 5
        tick_font = painter.font()
        tick_font.setPointSize(max(8, tick_font.pointSize() - 1))
        painter.setFont(tick_font)
        for i in range(tick_count + 1):
            t = i / tick_count
            value = y_min + t * (y_max - y_min)
            y = y_pos(value)
            painter.drawLine(plot_rect.left() - 4, y, plot_rect.left(), y)
            painter.drawText(
                4,
                int(y) + 4,
                left - 8,
                12,
                qt.align_right(),
                f'{value:.2f}',
            )

        if self._show_labels:
            painter.drawText(
                plot_rect.left(),
                rect.bottom() - 6,
                plot_rect.width(),
                18,
                qt.align_center(),
                'Calib number',
            )
            painter.drawText(
                4,
                top,
                left - 8,
                16,
                qt.align_left(),
                'FPA temp, C',
            )

        line_pen = qt.QtGui.QPen(qt.QtGui.QColor(220, 60, 60), 2)
        painter.setPen(line_pen)
        points = [
            qt.QtCore.QPointF(x_pos(i + 1), y_pos(temp)) for i, temp in enumerate(temps)
        ]
        painter.drawPolyline(qt.QtGui.QPolygonF(points))
        if self._show_points and self._point_radius > 0:
            painter.setBrush(qt.QtGui.QColor(220, 60, 60))
            radius = self._point_radius
            for point in points:
                painter.drawEllipse(point, radius, radius)


class TemperaturePlotWindow(qt.QtWidgets.QMainWindow):
    def __init__(self, on_close=None, parent=None):
        super().__init__(parent)
        self._temps = []
        self._on_close = on_close
        self.setWindowTitle('FPA temperature curve')
        self.resize(900, 600)

        central = qt.QtWidgets.QWidget()
        layout = qt.QtWidgets.QVBoxLayout(central)

        self.plot = InteractiveTemperaturePlot()
        layout.addWidget(self.plot, 1)

        controls = qt.QtWidgets.QWidget()
        controls_layout = qt.QtWidgets.QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.zoom_in = qt.QtWidgets.QToolButton()
        self.zoom_in.setText('Zoom In')
        self.zoom_in.clicked.connect(self.plot.zoom_in)
        self.zoom_out = qt.QtWidgets.QToolButton()
        self.zoom_out.setText('Zoom Out')
        self.zoom_out.clicked.connect(self.plot.zoom_out)
        self.zoom_reset = qt.QtWidgets.QToolButton()
        self.zoom_reset.setText('Reset')
        self.zoom_reset.clicked.connect(self.plot.reset_view)

        controls_layout.addWidget(self.zoom_in)
        controls_layout.addWidget(self.zoom_out)
        controls_layout.addWidget(self.zoom_reset)
        controls_layout.addStretch()
        layout.addWidget(controls)

        self.setCentralWidget(central)

    def closeEvent(self, event):
        if self._on_close:
            self._on_close()
        super().closeEvent(event)

    def set_temperatures(self, temps):
        self._temps = [float(value) for value in temps]
        self.plot.set_temperatures(self._temps)


def nice_step(span, max_ticks):
    if span <= 0:
        return 1.0
    raw = span / max_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    norm = raw / magnitude
    if norm < 1.5:
        return 1.0 * magnitude
    if norm < 3.0:
        return 2.0 * magnitude
    if norm < 7.0:
        return 5.0 * magnitude
    return 10.0 * magnitude


def compute_ticks(min_val, max_val, max_ticks):
    step = nice_step(max_val - min_val, max_ticks)
    if step <= 0:
        return [min_val, max_val], step
    start = math.ceil(min_val / step) * step
    ticks = []
    value = start
    limit = max_val + step * 0.5
    while value <= limit:
        ticks.append(value)
        value += step
    if not ticks:
        ticks = [min_val, max_val]
    return ticks, step


class InteractiveTemperaturePlot(qt.QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._temps = []
        self._x_range = None
        self._y_range = None
        self._default_range = None
        self._dragging = False
        self._last_pos = None
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)

    def set_temperatures(self, temps):
        self._temps = [float(value) for value in temps]
        self.reset_view()

    def reset_view(self):
        if not self._temps:
            self._x_range = None
            self._y_range = None
            self._default_range = None
            self.update()
            return
        count = len(self._temps)
        x_min = 1.0
        x_max = float(count)
        y_min = float(min(self._temps))
        y_max = float(max(self._temps))
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0
        y_pad = max((y_max - y_min) * 0.05, 1.0)
        y_min -= y_pad
        y_max += y_pad
        self._x_range = [x_min, x_max]
        self._y_range = [y_min, y_max]
        self._default_range = ([x_min, x_max], [y_min, y_max])
        self.update()

    def zoom_in(self):
        self._zoom(1 / 1.2)

    def zoom_out(self):
        self._zoom(1.2)

    def _zoom(self, factor, center=None):
        if not self._temps or not self._x_range or not self._y_range:
            return
        x_min, x_max = self._x_range
        y_min, y_max = self._y_range
        if center is None:
            center = ((x_min + x_max) / 2, (y_min + y_max) / 2)
        cx, cy = center
        span_x = (x_max - x_min) * factor
        span_y = (y_max - y_min) * factor
        if span_x <= 0 or span_y <= 0:
            return
        ratio_x = (cx - x_min) / (x_max - x_min) if x_max != x_min else 0.5
        ratio_y = (cy - y_min) / (y_max - y_min) if y_max != y_min else 0.5
        new_x_min = cx - ratio_x * span_x
        new_x_max = new_x_min + span_x
        new_y_min = cy - ratio_y * span_y
        new_y_max = new_y_min + span_y
        self._x_range = [new_x_min, new_x_max]
        self._y_range = [new_y_min, new_y_max]
        self.update()

    def _plot_rect(self):
        rect = self.rect()
        left = 120
        right = 20
        top = 24
        bottom = 90
        return rect.adjusted(left, top, -right, -bottom)

    def _data_to_screen(self, x, y, plot_rect):
        x_min, x_max = self._x_range
        y_min, y_max = self._y_range
        span_x = x_max - x_min or 1.0
        span_y = y_max - y_min or 1.0
        sx = plot_rect.left() + (x - x_min) / span_x * plot_rect.width()
        sy = plot_rect.bottom() - (y - y_min) / span_y * plot_rect.height()
        return sx, sy

    def _screen_to_data(self, pos, plot_rect):
        x_min, x_max = self._x_range
        y_min, y_max = self._y_range
        span_x = x_max - x_min or 1.0
        span_y = y_max - y_min or 1.0
        x = x_min + (pos.x() - plot_rect.left()) / plot_rect.width() * span_x
        y = y_min + (plot_rect.bottom() - pos.y()) / plot_rect.height() * span_y
        return x, y

    def wheelEvent(self, event):
        if not self._temps:
            return
        plot_rect = self._plot_rect()
        if not plot_rect.contains(event.position().toPoint()):
            center = None
        else:
            center = self._screen_to_data(event.position().toPoint(), plot_rect)
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1 / 1.2 if delta > 0 else 1.2
        self._zoom(factor, center=center)

    def mousePressEvent(self, event):
        if event.button() == qt.QtCore.Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._x_range and self._y_range:
            plot_rect = self._plot_rect()
            if plot_rect.width() <= 0 or plot_rect.height() <= 0:
                return
            pos = event.position().toPoint()
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            x_min, x_max = self._x_range
            y_min, y_max = self._y_range
            span_x = x_max - x_min
            span_y = y_max - y_min
            shift_x = -dx / plot_rect.width() * span_x
            shift_y = dy / plot_rect.height() * span_y
            self._x_range = [x_min + shift_x, x_max + shift_x]
            self._y_range = [y_min + shift_y, y_max + shift_y]
            self._last_pos = pos
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == qt.QtCore.Qt.MouseButton.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = qt.QtGui.QPainter(self)
        painter.setRenderHint(qt.QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        base_color = self.palette().color(palette_role('Base'))
        text_color = self.palette().color(palette_role('Text'))
        painter.fillRect(rect, base_color)

        if not self._temps or not self._x_range or not self._y_range:
            painter.setPen(text_color)
            painter.drawText(rect, qt.align_center(), 'No data')
            return

        plot_rect = self._plot_rect()
        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return

        axis_pen = qt.QtGui.QPen(text_color)
        grid_pen = qt.QtGui.QPen(qt.QtGui.QColor(120, 120, 120, 80))
        grid_pen.setStyle(qt.QtCore.Qt.PenStyle.DotLine)

        painter.setPen(axis_pen)
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.bottomRight())
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.topLeft())

        x_min, x_max = self._x_range
        y_min, y_max = self._y_range

        x_ticks, x_step = compute_ticks(x_min, x_max, 6)
        x_ticks = [tick for tick in x_ticks if tick >= 1.0]
        painter.setPen(grid_pen)
        for tick in x_ticks:
            x, _ = self._data_to_screen(tick, y_min, plot_rect)
            painter.drawLine(int(x), plot_rect.top(), int(x), plot_rect.bottom())

        y_ticks, y_step = compute_ticks(y_min, y_max, 6)
        for tick in y_ticks:
            _, y = self._data_to_screen(x_min, tick, plot_rect)
            painter.drawLine(plot_rect.left(), int(y), plot_rect.right(), int(y))

        painter.setPen(axis_pen)
        tick_font = painter.font()
        tick_font.setPointSize(max(8, tick_font.pointSize() - 1))
        painter.setFont(tick_font)

        for tick in x_ticks:
            x, _ = self._data_to_screen(tick, y_min, plot_rect)
            painter.drawLine(int(x), plot_rect.bottom(), int(x), plot_rect.bottom() + 4)
            painter.drawText(int(x) - 10, plot_rect.bottom() + 6, 40, 16, qt.align_left(), f'{tick:.0f}')

        for tick in y_ticks:
            _, y = self._data_to_screen(x_min, tick, plot_rect)
            painter.drawLine(plot_rect.left() - 4, int(y), plot_rect.left(), int(y))
            label = f'{tick:.2f}' if abs(y_step) < 1 else f'{tick:.0f}'
            painter.drawText(4, int(y) - 8, plot_rect.left() - 8, 16, qt.align_right(), label)

        painter.drawText(
            plot_rect.left(),
            rect.bottom() - 28,
            plot_rect.width(),
            18,
            qt.align_center(),
            'Calib number',
        )
        painter.drawText(
            6,
            plot_rect.top(),
            plot_rect.left() - 12,
            18,
            qt.align_left(),
            'FPA temperature, C',
        )

        line_pen = qt.QtGui.QPen(qt.QtGui.QColor(220, 60, 60), 2)
        painter.save()
        painter.setClipRect(plot_rect)
        painter.setPen(line_pen)
        points = []
        for i, temp in enumerate(self._temps):
            x = i + 1
            if x < x_min or x > x_max:
                continue
            sx, sy = self._data_to_screen(x, temp, plot_rect)
            points.append(qt.QtCore.QPointF(sx, sy))
        if points:
            painter.drawPolyline(qt.QtGui.QPolygonF(points))
            painter.setBrush(qt.QtGui.QColor(220, 60, 60))
            for point in points:
                painter.drawEllipse(point, 1.7, 1.7)
        painter.restore()


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
        self.plot_window = None
        self.last_detection = None
        self._build_ui()
        # Do not auto-open data folder; start with empty tabs.

    def _build_ui(self):
        central = qt.QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = qt.QtWidgets.QHBoxLayout(central)

        left_panel = qt.QtWidgets.QWidget()
        left_layout = qt.QtWidgets.QVBoxLayout(left_panel)
        left_panel.setSizePolicy(qt.QtWidgets.QSizePolicy.Policy.Expanding, qt.QtWidgets.QSizePolicy.Policy.Expanding)

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

        main_layout.addWidget(left_panel, 5)

        right_panel = qt.QtWidgets.QWidget()
        right_layout = qt.QtWidgets.QVBoxLayout(right_panel)
        right_panel.setMinimumWidth(360)

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
        mode_row = qt.QtWidgets.QWidget()
        mode_row_layout = qt.QtWidgets.QHBoxLayout(mode_row)
        mode_row_layout.setContentsMargins(0, 0, 0, 0)

        self.update_button = qt.QtWidgets.QToolButton()
        self.update_button.setToolTip('Update view')
        style = self.style()
        icon = None
        if hasattr(style, 'standardIcon') and hasattr(qt.QtWidgets.QStyle, 'StandardPixmap'):
            icon = style.standardIcon(qt.QtWidgets.QStyle.StandardPixmap.SP_BrowserReload)
        if icon is not None:
            self.update_button.setIcon(icon)
        else:
            self.update_button.setText('Update')
        self.update_button.clicked.connect(self.update_tiles)
        mode_row_layout.addWidget(self.update_button)

        self.mode_combo = qt.QtWidgets.QComboBox()
        for key in (MODE_RAW_LOCAL, MODE_RAW_GLOBAL, MODE_DIFF_MEAN):
            self.mode_combo.addItem(MODE_LABELS[key], key)
        self.mode_combo.addItem(MODE_LABELS[MODE_CALIB_INTERP], MODE_CALIB_INTERP)
        self.mode_combo.setCurrentIndex(self.mode_combo.count() - 1)
        mode_row_layout.addWidget(self.mode_combo, 1)
        right_layout.addWidget(mode_row)

        plot_header = qt.QtWidgets.QWidget()
        plot_header_layout = qt.QtWidgets.QHBoxLayout(plot_header)
        plot_header_layout.setContentsMargins(0, 0, 0, 0)
        plot_label = qt.QtWidgets.QLabel('FPA temperature curve:')
        plot_header_layout.addWidget(plot_label)

        self.plot_expand = qt.QtWidgets.QToolButton()
        self.plot_expand.setToolTip('Open plot window')
        self.plot_expand.clicked.connect(self.open_plot_window)
        style = self.style()
        if hasattr(style, 'standardIcon'):
            if hasattr(qt.QtWidgets.QStyle, 'StandardPixmap'):
                icon = style.standardIcon(qt.QtWidgets.QStyle.StandardPixmap.SP_TitleBarMaxButton)
            else:
                icon = style.standardIcon(qt.QtWidgets.QStyle.StandardPixmap.SP_TitleBarMaxButton)
            self.plot_expand.setIcon(icon)
        else:
            self.plot_expand.setText('Open')
        plot_header_layout.addWidget(self.plot_expand)
        plot_header_layout.addStretch()
        right_layout.addWidget(plot_header)

        self.temp_plot = TemperaturePlot(show_points=False, point_radius=0, show_labels=False)
        right_layout.addWidget(self.temp_plot, 2)

        self.detect_button = qt.QtWidgets.QPushButton('Detect first bad')
        self.detect_button.clicked.connect(self.detect_first_bad)
        right_layout.addWidget(self.detect_button)

        self.generate_button = qt.QtWidgets.QPushButton('Generate')
        self.generate_button.clicked.connect(self.generate_from_detection)
        right_layout.addWidget(self.generate_button)

        self.status_label = qt.QtWidgets.QLabel('')
        right_layout.addWidget(self.status_label)

        main_layout.addWidget(right_panel, 4)

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
        added_path = None
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
                added_path = norm
        if added_index is not None:
            self.folder_tabs.setCurrentIndex(added_index)
            if added_path:
                self.load_folder(added_path)

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
        self.last_detection = None
        self.temp_plot.set_temperatures([entry.temp_value for entry in self.entries])
        if self.plot_window:
            self.plot_window.set_temperatures([entry.temp_value for entry in self.entries])
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
        self.frame_cache.clear()
        self.frame_cache_i16.clear()
        self.frame_shape = None
        self.pixmap_refs = []
        self.global_scale = None
        self.temp_plot.set_temperatures([])
        if self.plot_window:
            self.plot_window.set_temperatures([])
        self.last_detection = None
        self.clear_tiles()
        self.status_label.setText('No folders opened.')

    def open_plot_window(self):
        if self.plot_window is None:
            self.plot_window = TemperaturePlotWindow(on_close=self._clear_plot_window, parent=self)
        self.plot_window.set_temperatures([entry.temp_value for entry in self.entries])
        self.plot_window.show()
        self.plot_window.raise_()
        self.plot_window.activateWindow()

    def _clear_plot_window(self):
        self.plot_window = None

    def get_selected_entries(self):
        return list(self.entries)

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

    def detect_first_bad(self):
        if not self.entries:
            self.status_label.setText('Detection: no data')
            return
        result = detect_bad(self.entries, self.get_frame_i16)
        self.last_detection = result
        outliers = result.get("outliers") or []
        outlier_text = ", ".join(entry.temp_str for entry in outliers) if outliers else ""
        if result["bad_idx"] is None:
            text = 'Detection: no bad frames'
            if result.get("threshold") is not None and result.get("baseline") is not None:
                text += f' (threshold {result["threshold"]:.2f}, baseline {result["baseline"]:.2f})'
            if outlier_text:
                text += f' | temp outliers: {outlier_text}'
            self.status_label.setText(text)
            return
        bad_idx = result["bad_idx"]
        bad_entry = result["bad_entry"]
        triple = (
            f'{self.entries[bad_idx].temp_str} | '
            f'{self.entries[bad_idx + 1].temp_str} | '
            f'{self.entries[bad_idx + 2].temp_str}'
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
        self.status_label.setText(text)

    def generate_from_detection(self):
        if not self.current_folder or not self.entries:
            self.status_label.setText('Generate: no folder loaded')
            return
        if self.last_detection is None:
            self.detect_first_bad()
        if not self.last_detection:
            return
        bad_entry = self.last_detection.get("bad_entry")
        bad_idx = self.last_detection.get("bad_idx")
        if not bad_entry:
            self.status_label.setText('Generate: bad frame not found')
            return
        start_temp = float(bad_entry.temp_value)
        if bad_idx is None or bad_idx <= 0:
            anchor_temp = start_temp
        else:
            anchor_temp = float(self.entries[bad_idx].temp_value)
        out_dir = make_output_dir(self.current_folder)
        clear_output_dir(out_dir)
        skip_temps = [
            float(entry.temp_value)
            for entry in self.entries
            if float(entry.temp_value) < start_temp
        ]
        generated = generate_into_folder(
            self.entries,
            start_temp,
            self.get_frame_i16,
            out_dir,
            degree=3,
            step=1.25,
            anchor_temp=anchor_temp,
            end_temp=70.0,
            skip_temps=skip_temps,
        )
        copy_original_entries(self.entries, self.current_folder, out_dir, start_temp)
        self.status_label.setText(
            f'Generate: wrote {len(generated)} raws from {anchor_temp:.2f} into {out_dir}'
        )
        self.add_folders([out_dir])


def main():
    app = qt.QtWidgets.QApplication(sys.argv)
    qt.apply_light_theme(app)
    window = RawModesWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
