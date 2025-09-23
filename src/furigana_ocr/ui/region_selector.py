"""Utility widget that lets the user pick a screen capture region."""

from __future__ import annotations

from math import ceil, floor
from typing import Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QRubberBand, QWidget

from ..core.models import Region


class RegionSelector(QWidget):
    """Fullscreen translucent widget that allows selecting a rectangular region."""

    region_selected = Signal(tuple)
    selection_cancelled = Signal()

    def __init__(self) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowState(Qt.WindowFullScreen)
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self._origin = QPoint()
        self._current_rect: Optional[QRect] = None
        self._last_ratio: float = 1.0

    def start(self) -> None:
        self._current_rect = None
        self._rubber_band.hide()
        self.show()
        QApplication.setOverrideCursor(Qt.CrossCursor)

    def stop(self) -> None:
        QApplication.restoreOverrideCursor()
        self.hide()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._origin = event.pos()
            self._rubber_band.setGeometry(QRect(self._origin, QSize(1, 1)))
            self._rubber_band.show()
        elif event.button() == Qt.RightButton:
            self._current_rect = None
            self._rubber_band.hide()
            self.selection_cancelled.emit()
            self.stop()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not self._rubber_band.isVisible():
            return
        rect = QRect(self._origin, event.pos()).normalized()
        self._rubber_band.setGeometry(rect)
        self._current_rect = rect
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton and self._rubber_band.isVisible():
            self._rubber_band.hide()
            rect = self._current_rect or QRect(self._origin, event.pos()).normalized()
            if rect.width() > 10 and rect.height() > 10:
                region = self._rect_to_region(rect)
                self.region_selected.emit(region)
            else:
                self.selection_cancelled.emit()
            self.stop()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setOpacity(0.3)
        painter.fillRect(self.rect(), Qt.black)
        painter.setOpacity(1.0)

    def _rect_to_region(self, rect: QRect) -> Region:
        top_left = self.mapToGlobal(rect.topLeft())
        screen = QApplication.screenAt(top_left)
        if screen is None:
            screen = QApplication.primaryScreen()
        ratio = float(screen.devicePixelRatio()) if screen is not None else 1.0
        self._last_ratio = ratio

        left = int(floor(top_left.x() * ratio))
        top = int(floor(top_left.y() * ratio))
        width = int(max(1, ceil(rect.width() * ratio)))
        height = int(max(1, ceil(rect.height() * ratio)))

        return (left, top, width, height)

    @property
    def last_ratio(self) -> float:
        return self._last_ratio


__all__ = ["RegionSelector"]
