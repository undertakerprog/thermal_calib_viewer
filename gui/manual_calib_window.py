import math

from gui import qt_compat as qt


def palette_role(name):
    if hasattr(qt.QtGui.QPalette, name):
        return getattr(qt.QtGui.QPalette, name)
    return getattr(qt.QtGui.QPalette.ColorRole, name)


try:
    Signal = qt.QtCore.pyqtSignal
except AttributeError:
    Signal = qt.QtCore.Signal


class ManualCalibPlot(qt.QtWidgets.QWidget):
    clicked_temp = Signal(float)
    double_clicked_temp = Signal(float)

    def __init__(self):
        super().__init__()
        self._temps = []
        self._points = []
        self._point_indices = []
        self._selected_index = None
        self._x_range = None
        self._y_range = None
        self._dragging = False
        self._last_pos = None
        self._moved = False
        self.setMinimumHeight(280)
        self.setMouseTracking(True)

    def set_temperatures(self, temps):
        self._temps = [float(value) for value in temps]
        self._selected_index = None
        self.reset_view()
        self.update()

    def reset_view(self):
        if not self._temps:
            self._x_range = None
            self._y_range = None
            return
        count = len(self._temps)
        x_min = 1.0
        x_max = float(count)
        y_min = min(self._temps)
        y_max = max(self._temps)
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0
        y_pad = max((y_max - y_min) * 0.05, 1.0)
        y_min -= y_pad
        y_max += y_pad
        self._x_range = [x_min, x_max]
        self._y_range = [y_min, y_max]

    def _plot_rect(self):
        rect = self.rect()
        left = 64
        right = 20
        top = 12
        bottom = 42
        return rect.adjusted(left, top, -right, -bottom)

    def _calc_points(self):
        self._points = []
        self._point_indices = []
        if not self._temps or not self._x_range or not self._y_range:
            return
        plot_rect = self._plot_rect()
        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return
        x_min, x_max = self._x_range
        y_min, y_max = self._y_range
        x_span = x_max - x_min or 1.0
        y_span = y_max - y_min or 1.0
        for i, temp in enumerate(self._temps):
            x = i + 1.0
            if x < x_min or x > x_max:
                continue
            sx = plot_rect.left() + (x - x_min) / x_span * plot_rect.width()
            sy = plot_rect.bottom() - (temp - y_min) / y_span * plot_rect.height()
            self._points.append(qt.QtCore.QPointF(sx, sy))
            self._point_indices.append(i)

    def _screen_to_data(self, pos):
        plot_rect = self._plot_rect()
        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return None
        if not self._x_range or not self._y_range:
            return None
        x_min, x_max = self._x_range
        y_min, y_max = self._y_range
        x = x_min + (pos.x() - plot_rect.left()) / plot_rect.width() * (x_max - x_min)
        y = y_min + (plot_rect.bottom() - pos.y()) / plot_rect.height() * (y_max - y_min)
        return x, y

    def _zoom(self, factor, center=None):
        if not self._x_range or not self._y_range:
            return
        x_min, x_max = self._x_range
        y_min, y_max = self._y_range
        if center is None:
            cx = (x_min + x_max) / 2.0
            cy = (y_min + y_max) / 2.0
        else:
            cx, cy = center
        span_x = (x_max - x_min) * factor
        span_y = (y_max - y_min) * factor
        if span_x <= 0 or span_y <= 0:
            return
        self._x_range = [cx - span_x / 2.0, cx + span_x / 2.0]
        self._y_range = [cy - span_y / 2.0, cy + span_y / 2.0]
        self.update()

    def wheelEvent(self, event):
        if not self._temps:
            return
        pos = event.position()
        center = self._screen_to_data(pos)
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1 / 1.2 if delta > 0 else 1.2
        self._zoom(factor, center=center)
        event.accept()

    def _find_nearest_index(self, pos):
        if not self._points:
            return None
        best_idx = None
        best_dist = None
        for i, point in enumerate(self._points):
            dx = point.x() - pos.x()
            dy = point.y() - pos.y()
            dist = math.hypot(dx, dy)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = i
        if best_dist is None or best_dist > 14.0:
            return None
        if best_idx >= len(self._point_indices):
            return None
        return self._point_indices[best_idx]

    def mousePressEvent(self, event):
        if event.button() == qt.QtCore.Qt.MouseButton.LeftButton:
            self._dragging = True
            self._moved = False
            self._last_pos = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._x_range and self._y_range:
            plot_rect = self._plot_rect()
            if plot_rect.width() <= 0 or plot_rect.height() <= 0:
                return
            pos = event.position()
            dx = pos.x() - self._last_pos.x()
            dy = pos.y() - self._last_pos.y()
            if abs(dx) > 1.0 or abs(dy) > 1.0:
                self._moved = True
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
            if not self._moved:
                idx = self._find_nearest_index(event.position())
                if idx is not None:
                    self._selected_index = idx
                    self.clicked_temp.emit(self._temps[idx])
                    self.update()
            self._dragging = False
            self._last_pos = None
            self._moved = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == qt.QtCore.Qt.MouseButton.LeftButton:
            idx = self._find_nearest_index(event.position())
            if idx is not None:
                self._selected_index = idx
                self.double_clicked_temp.emit(self._temps[idx])
                self.update()
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        painter = qt.QtGui.QPainter(self)
        painter.setRenderHint(qt.QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        base_color = self.palette().color(palette_role("Base"))
        text_color = self.palette().color(palette_role("Text"))
        painter.fillRect(rect, base_color)

        if not self._temps or not self._x_range or not self._y_range:
            painter.setPen(text_color)
            painter.drawText(rect, qt.align_center(), "No data")
            return

        plot_rect = self._plot_rect()
        if plot_rect.width() <= 0 or plot_rect.height() <= 0:
            return
        self._calc_points()

        axis_pen = qt.QtGui.QPen(text_color)
        painter.setPen(axis_pen)
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.bottomRight())
        painter.drawLine(plot_rect.bottomLeft(), plot_rect.topLeft())

        label_font = painter.font()
        label_font.setPointSize(max(8, label_font.pointSize() - 1))
        painter.setFont(label_font)
        painter.drawText(
            plot_rect.left(),
            rect.bottom() - 20,
            plot_rect.width(),
            16,
            qt.align_center(),
            "Calib number",
        )
        painter.drawText(
            4,
            4,
            58,
            16,
            qt.align_left(),
            "Temp, C",
        )

        line_pen = qt.QtGui.QPen(qt.QtGui.QColor(220, 60, 60), 2)
        painter.setPen(line_pen)
        painter.drawPolyline(qt.QtGui.QPolygonF(self._points))

        painter.setBrush(qt.QtGui.QColor(220, 60, 60))
        for i, point in enumerate(self._points):
            radius = 3.0 if i != self._selected_index else 4.5
            painter.drawEllipse(point, radius, radius)


class ManualCalibrationWindow(qt.QtWidgets.QDialog):
    apply_request = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual calibration")
        self.resize(860, 520)
        self._build_ui()

    def _build_ui(self):
        layout = qt.QtWidgets.QVBoxLayout(self)

        form = qt.QtWidgets.QGridLayout()
        row = 0

        form.addWidget(qt.QtWidgets.QLabel("Mode:"), row, 0)
        self.mode_combo = qt.QtWidgets.QComboBox()
        self.mode_combo.addItem("Bad tail (works)", "tail")
        self.mode_combo.addItem("Bad head (works)", "head")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addWidget(self.mode_combo, row, 1, 1, 3)
        row += 1

        self.from_label = qt.QtWidgets.QLabel("From:")
        form.addWidget(self.from_label, row, 0)
        self.from_edit = qt.QtWidgets.QLineEdit()
        self.from_edit.setPlaceholderText("empty = start of dataset")
        form.addWidget(self.from_edit, row, 1)

        self.to_label = qt.QtWidgets.QLabel("To:")
        form.addWidget(self.to_label, row, 2)
        self.to_edit = qt.QtWidgets.QLineEdit()
        self.to_edit.setPlaceholderText("double-click a point on plot")
        form.addWidget(self.to_edit, row, 3)
        row += 1

        self.selected_label = qt.QtWidgets.QLabel("Selected point: -")
        form.addWidget(self.selected_label, row, 0, 1, 4)
        row += 1

        self.hint_label = qt.QtWidgets.QLabel("")
        form.addWidget(self.hint_label, row, 0, 1, 4)
        layout.addLayout(form)

        self.plot = ManualCalibPlot()
        self.plot.clicked_temp.connect(self._on_plot_clicked)
        self.plot.double_clicked_temp.connect(self._on_plot_double_clicked)
        layout.addWidget(self.plot, 1)

        buttons = qt.QtWidgets.QHBoxLayout()
        buttons.addStretch()
        self.apply_button = qt.QtWidgets.QPushButton("Apply")
        self.apply_button.clicked.connect(self._emit_apply)
        buttons.addWidget(self.apply_button)
        close_button = qt.QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.close)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._on_mode_changed()

    def set_temperatures(self, temps):
        self.plot.set_temperatures(temps)

    def _on_plot_clicked(self, temp):
        self.selected_label.setText(f"Selected point: {temp:.2f} C")

    def _on_plot_double_clicked(self, temp):
        self._on_plot_clicked(temp)
        if self.mode_combo.currentData() == "tail":
            self.to_edit.setText(f"{temp:.2f}")
        else:
            self.from_edit.setText(f"{temp:.2f}")

    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        if mode == "tail":
            self.hint_label.setText(
                "Tail mode: set 'To' (bad starts after it). Double-click point -> To."
            )
            self.from_edit.setPlaceholderText("empty = start of dataset")
            self.to_edit.setPlaceholderText("required: bad starts after this temp")
        else:
            self.hint_label.setText(
                "Head mode: set good range [From..To]. Double-click point -> From."
            )
            self.from_edit.setPlaceholderText("required: first good temp")
            self.to_edit.setPlaceholderText("optional: last good temp (empty = dataset end)")

    def _emit_apply(self):
        mode = self.mode_combo.currentData()
        from_text = self.from_edit.text().strip()
        to_text = self.to_edit.text().strip()
        from_temp = None
        if from_text:
            try:
                from_temp = float(from_text)
            except ValueError:
                qt.QtWidgets.QMessageBox.warning(self, "Manual calibration", "Invalid 'From' value.")
                return
        to_temp = None
        if to_text:
            try:
                to_temp = float(to_text)
            except ValueError:
                qt.QtWidgets.QMessageBox.warning(self, "Manual calibration", "Invalid 'To' value.")
                return
        if mode == "tail" and to_temp is None:
            qt.QtWidgets.QMessageBox.warning(self, "Manual calibration", "In tail mode 'To' is required.")
            return
        if mode == "head" and from_temp is None:
            qt.QtWidgets.QMessageBox.warning(self, "Manual calibration", "In head mode 'From' is required.")
            return
        self.apply_request.emit(
            {
                "mode": mode,
                "from_temp": from_temp,
                "to_temp": to_temp,
            }
        )
