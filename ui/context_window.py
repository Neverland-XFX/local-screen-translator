from collections import deque

from PySide6 import QtCore, QtGui, QtWidgets

from utils.text import similarity


class ContextWindow(QtWidgets.QWidget):
    def __init__(self, config: dict) -> None:
        super().__init__()
        ui_cfg = config.get("ui", {})
        ctx_cfg = ui_cfg.get("context", {})
        translate_cfg = config.get("translate", {})

        flags = QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool
        self.setWindowFlags(flags)
        self.setWindowTitle("Context")
        self.setWindowOpacity(ctx_cfg.get("opacity", 0.95))

        self._max_entries = int(ctx_cfg.get("max_entries", 12))
        self._show_original = bool(ctx_cfg.get("show_original", True))
        self._show_translation = bool(ctx_cfg.get("show_translation", True))
        self._update_similarity = float(ctx_cfg.get("update_similarity", 0.85))
        self._src_label = str(translate_cfg.get("from", "src")).upper()
        self._dst_label = str(translate_cfg.get("to", "dst")).upper()
        self._entries = deque(maxlen=self._max_entries)

        font_family = ui_cfg.get("font_family", "Segoe UI")
        font_size = int(ctx_cfg.get("font_size", max(12, ui_cfg.get("font_size", 20) - 6)))
        font = QtGui.QFont(font_family, font_size)

        self._text = QtWidgets.QPlainTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setFont(font)
        self._text.setStyleSheet(
            "background: rgba(0, 0, 0, 180); color: #ffffff; padding: 8px;"
        )
        self._text.setMaximumWidth(int(ctx_cfg.get("max_width", 520)))
        self._text.setMaximumHeight(int(ctx_cfg.get("max_height", 320)))

        clear_btn = QtWidgets.QPushButton("Clear", self)
        clear_btn.clicked.connect(self.clear_entries)

        header = QtWidgets.QHBoxLayout()
        header.addWidget(QtWidgets.QLabel("Context", self))
        header.addStretch(1)
        header.addWidget(clear_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(header)
        layout.addWidget(self._text)

    @QtCore.Slot(str, str)
    def append_entry(self, original: str, translation: str) -> None:
        original = original.strip()
        translation = translation.strip()
        if not original and not translation:
            return

        if self._entries:
            last_original, _last_translation = self._entries[-1]
            if similarity(original, last_original) >= self._update_similarity:
                self._entries[-1] = (original, translation)
                self._refresh()
                return

        self._entries.append((original, translation))
        self._refresh()

    @QtCore.Slot()
    def clear_entries(self) -> None:
        self._entries.clear()
        self._refresh()

    def _refresh(self) -> None:
        lines = []
        for original, translation in self._entries:
            if self._show_original and original:
                lines.append(f"{self._src_label}: {original}")
            if self._show_translation and translation:
                lines.append(f"{self._dst_label}: {translation}")
            lines.append("")
        text = "\n".join(lines).strip()
        self._text.setPlainText(text)
        self._text.verticalScrollBar().setValue(self._text.verticalScrollBar().maximum())

    def position_for_roi(self, roi_logical) -> None:
        left, top, right, _bottom = roi_logical
        self.adjustSize()

        margin = 12
        x = right + margin
        y = top

        screen_rect = QtGui.QGuiApplication.primaryScreen().virtualGeometry()
        if x + self.width() > screen_rect.right():
            x = left - self.width() - margin
        if x < screen_rect.left():
            x = screen_rect.left() + margin
        if y + self.height() > screen_rect.bottom():
            y = screen_rect.bottom() - self.height() - margin

        self.move(x, y)
