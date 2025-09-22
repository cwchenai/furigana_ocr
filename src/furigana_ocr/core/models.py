"""Data models shared across the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

Region = Tuple[int, int, int, int]
"""A screen capture region defined as ``(left, top, width, height)``."""


@dataclass(slots=True)
class BoundingBox:
    """A helper structure describing a rectangle on screen."""

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def translated(self, dx: int, dy: int) -> "BoundingBox":
        return BoundingBox(self.left + dx, self.top + dy, self.width, self.height)

    def to_tuple(self) -> Region:
        return (self.left, self.top, self.width, self.height)

    @staticmethod
    def from_points(points: Iterable[Tuple[int, int]]) -> "BoundingBox":
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        left, right = min(xs), max(xs)
        top, bottom = min(ys), max(ys)
        return BoundingBox(left, top, right - left, bottom - top)


@dataclass(slots=True)
class OCRWord:
    """A single OCR token as produced by Tesseract."""

    text: str
    confidence: float
    bbox: BoundingBox
    order: int


@dataclass(slots=True)
class OCRResult:
    """The aggregate OCR result for a captured frame."""

    text: str
    words: List[OCRWord] = field(default_factory=list)


@dataclass(slots=True)
class TokenData:
    """Result from the tokeniser for a single lexical entry."""

    surface: str
    reading: Optional[str] = None
    lemma: Optional[str] = None
    part_of_speech: Optional[str] = None


@dataclass(slots=True)
class DictionaryEntry:
    """Dictionary information for a token."""

    expression: str
    reading: Optional[str]
    senses: Sequence[str]

    def format_gloss(self) -> str:
        return "; ".join(self.senses)


@dataclass(slots=True)
class TokenAnnotation:
    """Enriched token information used by the overlay."""

    token: TokenData
    furigana: Optional[str]
    bbox: Optional[BoundingBox]
    confidence: float
    dictionary_entries: Sequence[DictionaryEntry] = field(default_factory=list)


__all__ = [
    "BoundingBox",
    "DictionaryEntry",
    "OCRResult",
    "OCRWord",
    "Region",
    "TokenAnnotation",
    "TokenData",
]
