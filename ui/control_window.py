from PySide6 import QtCore, QtGui, QtWidgets


class ControlWindow(QtWidgets.QWidget):
    reselect_requested = QtCore.Signal()
    context_toggle_requested = QtCore.Signal()
    mode_changed = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        flags = QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._mode_combo = QtWidgets.QComboBox(self)
        self._mode_combo.addItem("OCR", "ocr")
        self._mode_combo.addItem("Text Hook", "text_hook_clipboard")
        self._mode_combo.addItem("Captions", "caption_http")
        self._mode_combo.currentIndexChanged.connect(self._emit_mode)

        select_btn = QtWidgets.QPushButton("Select ROI", self)
        select_btn.clicked.connect(self.reselect_requested.emit)

        context_btn = QtWidgets.QPushButton("Context", self)
        context_btn.clicked.connect(self.context_toggle_requested.emit)

        mode_row = QtWidgets.QHBoxLayout()
        mode_row.addWidget(QtWidgets.QLabel("Mode:", self))
        mode_row.addWidget(self._mode_combo)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(mode_row)
        layout.addWidget(select_btn)
        layout.addWidget(context_btn)

        self.adjustSize()

    def set_mode(self, mode: str) -> None:
        idx = self._mode_combo.findData(mode)
        if idx >= 0:
            self._mode_combo.setCurrentIndex(idx)

    def _emit_mode(self) -> None:
        self.mode_changed.emit(self._mode_combo.currentData())

    def position_for_roi(self, roi_logical) -> None:
        left, top, _right, _bottom = roi_logical
        self.adjustSize()

        margin = 8
        x = left
        y = top - self.height() - margin

        screen_rect = QtGui.QGuiApplication.primaryScreen().virtualGeometry()
        if y < screen_rect.top():
            y = top + margin
        x = max(screen_rect.left(), min(x, screen_rect.right() - self.width()))
        y = max(screen_rect.top(), min(y, screen_rect.bottom() - self.height()))
        self.move(x, y)
