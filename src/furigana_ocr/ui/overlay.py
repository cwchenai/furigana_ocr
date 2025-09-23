"""Overlay widget used to display furigana annotations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QToolTip, QWidget

from ..config import OverlayConfig
from ..core.models import BoundingBox, TokenAnnotation


@dataclass(slots=True)
class OverlayState:
    region: tuple[int, int, int, int]
    annotations: Sequence[TokenAnnotation]
    device_pixel_ratio: float = 1.0


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
        ratio = state.device_pixel_ratio if state.device_pixel_ratio > 0 else 1.0
        scale = 1.0 / ratio

        region = state.region
        logical_region = (
            int(round(region[0] * scale)),
            int(round(region[1] * scale)),
            max(int(round(region[2] * scale)), 1),
            max(int(round(region[3] * scale)), 1),
        )
        self.setGeometry(*logical_region)
        self._rebuild_labels(state.annotations, scale)
        if state.annotations:
            self.show()
        else:
            self.hide()

    def _rebuild_labels(
        self, annotations: Sequence[TokenAnnotation], scale: float
    ) -> None:
        self.clear()
        for annotation in annotations:
            if annotation.bbox is None:
                continue
            label = TokenLabel(annotation, self._config, self)
            bbox = annotation.bbox
            scaled_bbox = BoundingBox(
                left=int(round(bbox.left * scale)),
                top=int(round(bbox.top * scale)),
                width=max(int(round(bbox.width * scale)), 1),
                height=max(int(round(bbox.height * scale)), 1),
            )
            label.apply_bbox(scaled_bbox)
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
        self._surface_font = QFont(self.config.font_family, self.config.font_size)
        if annotation.furigana:
            self._furigana_font = QFont(self.config.font_family, self.config.furigana_font_size)
            self._furigana_height = QFontMetrics(self._furigana_font).height()
        else:
            self._furigana_font = None
            self._furigana_height = 0
        self._surface_offset = 0
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

    def apply_bbox(self, bbox: BoundingBox) -> None:
        """Resize and position the widget to accommodate furigana above the text."""

        if self._furigana_height:
            desired_top = bbox.top - self._furigana_height
        else:
            desired_top = bbox.top
        new_top = max(desired_top, 0)
        self._surface_offset = bbox.top - new_top
        height = max(self._surface_offset + bbox.height, 1)
        self.setGeometry(bbox.left, new_top, bbox.width, height)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        background = QColor(0, 0, 0)
        background.setAlphaF(min(max(self.config.background_opacity, 0.0), 0.8))
        if background.alpha() > 0:
            painter.fillRect(self.rect(), background)

        furigana_text = self.annotation.furigana
        if furigana_text and self._furigana_font is not None:
            painter.setFont(self._furigana_font)
            painter.setPen(QColor(255, 200, 150))
            furigana_bottom = self._surface_offset
            if furigana_bottom <= 0:
                furigana_rect = QRect(0, 0, self.width(), min(self._furigana_height, self.height()))
            else:
                furigana_top = max(furigana_bottom - self._furigana_height, 0)
                rect_height = max(furigana_bottom - furigana_top, 1)
                furigana_rect = QRect(0, furigana_top, self.width(), rect_height)
            painter.drawText(furigana_rect, Qt.AlignHCenter | Qt.AlignBottom, furigana_text)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        tooltip = self.toolTip()
        if tooltip:
            QToolTip.showText(QCursor.pos(), tooltip, self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        QToolTip.hideText()
        super().leaveEvent(event)


__all__ = ["OverlayState", "OverlayWindow"]
