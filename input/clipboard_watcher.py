from PySide6 import QtCore, QtGui


class ClipboardWatcher(QtCore.QObject):
    def __init__(self, poll_ms: int, on_text) -> None:
        super().__init__()
        self._on_text = on_text
        self._clipboard = QtGui.QGuiApplication.clipboard()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(max(50, int(poll_ms)))
        self._timer.timeout.connect(self._poll)
        self._last_text = ""
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._last_text = ""
        self._timer.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._timer.stop()
        self._running = False

    def _poll(self) -> None:
        if not self._running:
            return
        text = self._clipboard.text()
        if not text:
            return
        text = text.strip()
        if not text or text == self._last_text:
            return
        self._last_text = text
        self._on_text(text)
