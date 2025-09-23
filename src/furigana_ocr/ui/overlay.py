"""Overlay widget used to display furigana annotations."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import List, Sequence, cast

from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QScreen,
)
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

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
        self._dictionary_popup = DictionaryPopup(self)
        self.hide()

    def notify_config_changed(self) -> None:
        """Propagate configuration updates to existing labels."""

        for label in self._labels:
            label.update_config(self._config)

    def clear(self) -> None:
        self._dictionary_popup.hide_popup()
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

    def show_dictionary(self, label: "TokenLabel") -> None:
        anchor = QRect(label.mapToGlobal(QPoint(0, 0)), label.rect().size())
        if not self._dictionary_popup.show_for(label.annotation, anchor, self.screen()):
            self._dictionary_popup.hide_popup()

    def hide_dictionary(self, label: "TokenLabel") -> None:
        self._dictionary_popup.hide_popup()


class TokenLabel(QWidget):
    """Interactive widget responsible for rendering a single token."""

    def __init__(self, annotation: TokenAnnotation, config: OverlayConfig, parent: QWidget) -> None:
        super().__init__(parent)
        self.annotation = annotation
        self.config = config
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self._surface_font = QFont()
        self._furigana_font: QFont | None = None
        self._furigana_height = 0
        self._surface_offset = 0
        self._bbox: BoundingBox | None = None
        self._is_hovered = False
        self._overlay = cast(OverlayWindow, parent)
        self._update_fonts()
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
        self._bbox = bbox

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

        if self._is_hovered:
            highlight_color = QColor(*self.config.furigana_color)
            highlight_color.setAlpha(220)
            highlight_pen = QPen(highlight_color, 2)
            painter.setPen(highlight_pen)
            painter.setBrush(Qt.transparent)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        furigana_text = self.annotation.furigana
        if furigana_text and self._furigana_font is not None:
            painter.setFont(self._furigana_font)
            furigana_bottom = self._surface_offset
            if furigana_bottom <= 0:
                furigana_rect = QRect(0, 0, self.width(), min(self._furigana_height, self.height()))
            else:
                furigana_top = max(furigana_bottom - self._furigana_height, 0)
                rect_height = max(furigana_bottom - furigana_top, 1)
                furigana_rect = QRect(0, furigana_top, self.width(), rect_height)
            metrics = QFontMetrics(self._furigana_font)
            text_width = metrics.horizontalAdvance(furigana_text)
            x = furigana_rect.left() + max((furigana_rect.width() - text_width) / 2.0, 0.0)
            baseline = furigana_rect.bottom() - metrics.descent()
            path = QPainterPath()
            path.addText(x, float(baseline), self._furigana_font, furigana_text)
            fill_color = QColor(*self.config.furigana_color)
            outline = QColor(0, 0, 0)
            outline.setAlpha(170)
            outline_pen = QPen(outline, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            outline_pen.setWidthF(1.0)
            painter.setPen(outline_pen)
            painter.setBrush(fill_color)
            painter.drawPath(path)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._is_hovered = True
        self._overlay.show_dictionary(self)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._is_hovered = False
        self._overlay.hide_dictionary(self)
        self.update()
        super().leaveEvent(event)

    def update_config(self, config: OverlayConfig) -> None:
        """Refresh the widget fonts and repaint using the new configuration."""

        self.config = config
        self._update_fonts()
        if self._bbox is not None:
            self.apply_bbox(self._bbox)
        else:
            self.update()

    def _update_fonts(self) -> None:
        self._surface_font = QFont(self.config.font_family, self.config.font_size)
        if self.annotation.furigana:
            furigana_font = QFont(self.config.font_family, self.config.furigana_font_size)
            furigana_font.setBold(True)
            self._furigana_font = furigana_font
            self._furigana_height = QFontMetrics(furigana_font).height()
        else:
            self._furigana_font = None
            self._furigana_height = 0


__all__ = ["OverlayState", "OverlayWindow"]


class DictionaryPopup(QWidget):
    """Rich tooltip widget that displays dictionary information."""

    _MAX_WIDTH = 360

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setObjectName("dictionaryPopup")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        self._content = QLabel(self)
        self._content.setObjectName("dictionaryPopupContent")
        self._content.setWordWrap(True)
        self._content.setTextFormat(Qt.RichText)
        self._content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._content.setMaximumWidth(self._MAX_WIDTH)
        layout.addWidget(self._content)
        self.setStyleSheet(
            "#dictionaryPopup {"
            "background-color: rgba(255, 255, 255, 245);"
            "border: 1px solid rgba(0, 0, 0, 80);"
            "border-radius: 8px;"
            "color: #222;"
            "font-size: 13px;"
            "}"
            "#dictionaryPopupContent {"
            "color: #222;"
            "}""
        )

    def show_for(
        self,
        annotation: TokenAnnotation,
        anchor: QRect,
        screen: QScreen | None,
    ) -> bool:
        html = self._build_html(annotation)
        if html is None:
            return False
        self._content.setText(html)
        self._content.adjustSize()
        self.adjustSize()
        offset = 12
        x = anchor.right() + offset
        y = anchor.top()
        if screen is not None:
            available = screen.availableGeometry()
            if x + self.width() > available.right() - offset:
                x = anchor.left() - self.width() - offset
            if x < available.left() + offset:
                x = available.left() + offset
            if y + self.height() > available.bottom() - offset:
                y = anchor.bottom() - self.height()
            if y < available.top() + offset:
                y = available.top() + offset
        self.move(int(x), int(y))
        self.show()
        self.raise_()
        return True

    def hide_popup(self) -> None:
        self.hide()

    def _build_html(self, annotation: TokenAnnotation) -> str | None:
        token = annotation.token
        header_parts: List[str] = []
        surface = token.surface.strip()
        if surface:
            header = f"<span style='font-weight:bold; font-size:14px;'>{escape(surface)}</span>"
            header_parts.append(header)
        if token.reading and token.reading.strip() and token.reading.strip() != surface:
            header_parts.append(
                f"<span style='color:#666;'>[{escape(token.reading.strip())}]</span>"
            )
        details: List[str] = []
        if token.part_of_speech:
            details.append(escape(token.part_of_speech))
        if token.lemma and token.lemma.strip() and token.lemma.strip() != surface:
            details.append(f"原形: {escape(token.lemma.strip())}")

        body_sections: List[str] = []
        if header_parts:
            header_html = "&nbsp;".join(header_parts)
            if details:
                header_html += "<div style='color:#777; margin-top:2px;'>" + " / ".join(details) + "</div>"
            body_sections.append(header_html)
        elif details:
            body_sections.append("<div style='color:#777;'>" + " / ".join(details) + "</div>")

        for entry in annotation.dictionary_entries:
            expression = escape(entry.expression)
            reading_html = (
                f"<span style='color:#555;'>[{escape(entry.reading)}]</span>"
                if entry.reading and entry.reading != entry.expression
                else ""
            )
            gloss_items = "".join(
                f"<li>{escape(sense)}</li>" for sense in entry.senses if sense.strip()
            )
            gloss_html = (
                f"<ul style='margin:4px 0 0 18px; padding:0;'>" + gloss_items + "</ul>"
                if gloss_items
                else ""
            )
            entry_html = (
                f"<div style='margin-top:6px;'><span style='font-weight:bold;'>{expression}</span>"
                f" {reading_html}{gloss_html}</div>"
            )
            body_sections.append(entry_html)

        if not body_sections:
            return None
        return "".join(body_sections)
