"""Overlay widget used to display furigana annotations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QToolTip, QWidget

from ..config import OverlayConfig
from ..core.models import TokenAnnotation


@dataclass(slots=True)
class OverlayState:
    region: tuple[int, int, int, int]
    annotations: Sequence[TokenAnnotation]


class OverlayWindow(QWidget):
    """A frameless transparent window that renders token annotations."""

    def __init__(self, config: OverlayConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setMouseTracking(True)
        self._config = config
        self._labels: List[TokenLabel] = []
        self.hide()

    def clear(self) -> None:
        for label in self._labels:
            label.setParent(None)
            label.deleteLater()
        self._labels.clear()
        self.hide()

    def update_state(self, state: OverlayState | None) -> None:
        if state is None:
            self.clear()
            return
        region = state.region
        self.setGeometry(region[0], region[1], region[2], region[3])
        self._rebuild_labels(state.annotations)
        if state.annotations:
            self.show()
        else:
            self.hide()

    def _rebuild_labels(self, annotations: Sequence[TokenAnnotation]) -> None:
        self.clear()
        for annotation in annotations:
            if annotation.bbox is None:
                continue
            label = TokenLabel(annotation, self._config, self)
            label.move(annotation.bbox.left, annotation.bbox.top)
            label.resize(annotation.bbox.width, annotation.bbox.height)
            label.show()
            self._labels.append(label)


class TokenLabel(QWidget):
    """Interactive widget responsible for rendering a single token."""

    def __init__(self, annotation: TokenAnnotation, config: OverlayConfig, parent: QWidget) -> None:
        super().__init__(parent)
        self.annotation = annotation
        self.config = config
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        if annotation.dictionary_entries:
            tooltip_lines = [
                f"<b>{entry.expression}</b> ({entry.reading}) - {entry.format_gloss()}"
                if entry.reading
                else f"<b>{entry.expression}</b> - {entry.format_gloss()}"
                for entry in annotation.dictionary_entries
            ]
            self.setToolTip("<br/>".join(tooltip_lines))
        else:
            self.setToolTip("")

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        background = QColor(0, 0, 0)
        background.setAlphaF(min(max(self.config.background_opacity, 0.0), 0.8))
        if background.alpha() > 0:
            painter.fillRect(self.rect(), background)

        surface_font = QFont(self.config.font_family, self.config.font_size)
        painter.setFont(surface_font)
        surface_metrics = QFontMetrics(surface_font)
        surface_height = surface_metrics.height()

        furigana_text = self.annotation.furigana
        furigana_height = 0
        if furigana_text:
            furigana_font = QFont(self.config.font_family, self.config.furigana_font_size)
            painter.setFont(furigana_font)
            furigana_metrics = QFontMetrics(furigana_font)
            furigana_height = furigana_metrics.height()
        else:
            furigana_font = None

        total_height = surface_height + furigana_height
        y_offset = max((self.height() - total_height) // 2, 0)

        if furigana_text and furigana_font is not None:
            painter.setFont(furigana_font)
            painter.setPen(QColor(255, 200, 150))
            furigana_rect = self.rect().adjusted(0, y_offset, 0, 0)
            painter.drawText(furigana_rect, Qt.AlignHCenter | Qt.AlignTop, furigana_text)
            y_offset += furigana_height

        painter.setFont(surface_font)
        painter.setPen(QColor(255, 255, 255))
        surface_rect = self.rect().adjusted(0, y_offset, 0, 0)
        painter.drawText(surface_rect, Qt.AlignHCenter | Qt.AlignTop, self.annotation.token.surface)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        tooltip = self.toolTip()
        if tooltip:
            QToolTip.showText(QCursor.pos(), tooltip, self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        QToolTip.hideText()
        super().leaveEvent(event)


__all__ = ["OverlayState", "OverlayWindow"]
