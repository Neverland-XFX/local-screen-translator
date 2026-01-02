from PySide6 import QtCore, QtGui, QtWidgets


class SelectionWindow(QtWidgets.QWidget):
    roi_selected = QtCore.Signal(tuple)

    def __init__(self) -> None:
        super().__init__()
        flags = QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setCursor(QtCore.Qt.CrossCursor)

        self._origin = None
        self._current = None

    def activate(self) -> None:
        geom = QtGui.QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geom)
        self.show()
        self.raise_()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        self._origin = event.position()
        self._current = event.position()
        self.update()

    def mouseMoveEvent(self, event):
        if self._origin is None:
            return
        self._current = event.position()
        self.update()

    def mouseReleaseEvent(self, event):
        if self._origin is None or self._current is None:
            return
        p1 = self.mapToGlobal(self._origin.toPoint())
        p2 = self.mapToGlobal(self._current.toPoint())
        left = min(p1.x(), p2.x())
        top = min(p1.y(), p2.y())
        right = max(p1.x(), p2.x())
        bottom = max(p1.y(), p2.y())

        if (right - left) < 10 or (bottom - top) < 10:
            self._origin = None
            self._current = None
            self.update()
            return

        self.hide()
        self.roi_selected.emit((left, top, right, bottom))
        self._origin = None
        self._current = None
        self.update()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            QtWidgets.QApplication.quit()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        overlay = QtGui.QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay)

        if self._origin is None or self._current is None:
            return

        rect = QtCore.QRectF(self._origin, self._current).normalized()
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
        painter.fillRect(rect, QtGui.QColor(0, 0, 0, 0))
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)

        pen = QtGui.QPen(QtGui.QColor(0, 170, 255), 2)
        painter.setPen(pen)
        painter.drawRect(rect)
