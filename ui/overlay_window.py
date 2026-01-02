from PySide6 import QtCore, QtGui, QtWidgets


class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self._config = config
        ui_cfg = config["ui"]
        translate_cfg = config.get("translate", {})
        self._source_label = str(translate_cfg.get("from", "src")).upper()

        flags = QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool
        if ui_cfg.get("click_through", True):
            flags |= QtCore.Qt.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowOpacity(ui_cfg.get("opacity", 0.95))

        self._label = QtWidgets.QLabel("", self)
        self._label.setWordWrap(True)
        self._label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._label.setStyleSheet(
            "color: white; background: rgba(0, 0, 0, 160); padding: 8px; border-radius: 6px;"
        )
        font = QtGui.QFont(ui_cfg.get("font_family", "Segoe UI"), ui_cfg.get("font_size", 20))
        self._label.setFont(font)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        self._raw_label = QtWidgets.QLabel("", self)
        self._raw_label.setWordWrap(True)
        self._raw_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._raw_label.setStyleSheet(
            "color: #cccccc; background: rgba(0, 0, 0, 120); padding: 6px; border-radius: 6px;"
        )
        raw_font = QtGui.QFont(ui_cfg.get("font_family", "Segoe UI"), max(10, ui_cfg.get("font_size", 20) - 6))
        self._raw_label.setFont(raw_font)
        layout.addWidget(self._raw_label)
        self._raw_label.hide()
        self._status_label = QtWidgets.QLabel("", self)
        self._status_label.setWordWrap(True)
        self._status_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self._status_label.setStyleSheet(
            "color: #ffcc66; background: rgba(0, 0, 0, 120); padding: 6px; border-radius: 6px;"
        )
        status_font = QtGui.QFont(ui_cfg.get("font_family", "Segoe UI"), max(10, ui_cfg.get("font_size", 20) - 6))
        self._status_label.setFont(status_font)
        layout.addWidget(self._status_label)
        self._status_label.hide()

    def update_text(self, text: str) -> None:
        self._label.setText(text)
        self._label.adjustSize()
        self.adjustSize()

    def update_raw_text(self, text: str) -> None:
        if not text:
            self._raw_label.hide()
            return
        self._raw_label.setText(f"{self._source_label}: {text}")
        self._raw_label.show()
        self._raw_label.adjustSize()
        self.adjustSize()

    def update_status(self, text: str) -> None:
        if not text:
            self._status_label.hide()
            return
        self._status_label.setText(f"Status: {text}")
        self._status_label.show()
        self._status_label.adjustSize()
        self.adjustSize()

    def position_for_roi(self, roi_logical) -> None:
        ui_cfg = self._config["ui"]
        mode = ui_cfg.get("mode", "subtitle")
        max_width = ui_cfg.get("max_width", 900)
        left, top, right, bottom = roi_logical

        self._label.setMaximumWidth(max_width)
        self.adjustSize()

        if mode == "subtitle":
            x = left
            y = bottom + 8
        else:
            x = right + 8
            y = top

        screen_rect = QtGui.QGuiApplication.primaryScreen().virtualGeometry()
        x = max(screen_rect.left(), min(x, screen_rect.right() - self.width()))
        y = max(screen_rect.top(), min(y, screen_rect.bottom() - self.height()))
        self.move(x, y)
