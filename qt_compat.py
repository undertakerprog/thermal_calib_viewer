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


def keep_aspect_ratio():
    if hasattr(QtCore.Qt, 'KeepAspectRatio'):
        return QtCore.Qt.KeepAspectRatio
    return QtCore.Qt.AspectRatioMode.KeepAspectRatio


def fast_transform():
    if hasattr(QtCore.Qt, 'FastTransformation'):
        return QtCore.Qt.FastTransformation
    return QtCore.Qt.TransformationMode.FastTransformation


def align_top_left():
    if hasattr(QtCore.Qt, 'AlignTop'):
        return QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
    return QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft


def align_center():
    if hasattr(QtCore.Qt, 'AlignCenter'):
        return QtCore.Qt.AlignCenter
    return QtCore.Qt.AlignmentFlag.AlignCenter


def align_left():
    if hasattr(QtCore.Qt, 'AlignLeft'):
        return QtCore.Qt.AlignLeft
    return QtCore.Qt.AlignmentFlag.AlignLeft


def align_right():
    if hasattr(QtCore.Qt, 'AlignRight'):
        return QtCore.Qt.AlignRight
    return QtCore.Qt.AlignmentFlag.AlignRight


def qimage_format_grayscale8():
    if hasattr(QtGui.QImage, 'Format_Grayscale8'):
        return QtGui.QImage.Format_Grayscale8
    return QtGui.QImage.Format.Format_Grayscale8


def _palette_role(name):
    if hasattr(QtGui.QPalette, name):
        return getattr(QtGui.QPalette, name)
    return getattr(QtGui.QPalette.ColorRole, name)


def apply_light_theme(app):
    if hasattr(app, 'setStyle'):
        app.setStyle('Fusion')
    palette = QtGui.QPalette()
    palette.setColor(_palette_role('Window'), QtGui.QColor(245, 245, 245))
    palette.setColor(_palette_role('WindowText'), QtGui.QColor(0, 0, 0))
    palette.setColor(_palette_role('Base'), QtGui.QColor(255, 255, 255))
    palette.setColor(_palette_role('AlternateBase'), QtGui.QColor(240, 240, 240))
    palette.setColor(_palette_role('ToolTipBase'), QtGui.QColor(255, 255, 255))
    palette.setColor(_palette_role('ToolTipText'), QtGui.QColor(0, 0, 0))
    palette.setColor(_palette_role('Text'), QtGui.QColor(0, 0, 0))
    palette.setColor(_palette_role('Button'), QtGui.QColor(240, 240, 240))
    palette.setColor(_palette_role('ButtonText'), QtGui.QColor(0, 0, 0))
    palette.setColor(_palette_role('BrightText'), QtGui.QColor(255, 0, 0))
    palette.setColor(_palette_role('Link'), QtGui.QColor(0, 102, 204))
    palette.setColor(_palette_role('Highlight'), QtGui.QColor(76, 163, 224))
    palette.setColor(_palette_role('HighlightedText'), QtGui.QColor(0, 0, 0))
    app.setPalette(palette)


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
