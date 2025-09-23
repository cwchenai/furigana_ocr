"""Application level configuration objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class CaptureConfig:
    """Configuration that controls how screenshots are captured."""

    frequency_ms: int = 3000
    """Polling frequency for OCR updates in milliseconds."""

    language: str = "jpn"
    """Tesseract language pack to use for OCR."""

    engine: str = "tesseract"
    """OCR engine identifier (``"tesseract"`` or ``"paddle"``)."""

    psm: int = 6
    """Page segmentation mode for Tesseract."""

    oem: int = 3
    """OCR engine mode for Tesseract."""

    tesseract_cmd: Optional[Path] = None
    """Optional path to the Tesseract executable."""


@dataclass(slots=True)
class OverlayConfig:
    """Visual configuration for the overlay window."""

    font_family: str = "Noto Sans CJK JP"
    font_size: int = 18
    furigana_font_size: int = 11
    background_opacity: float = 0.0


@dataclass(slots=True)
class DictionaryConfig:
    """Configuration related to dictionary lookups."""

    search_limit: int = 3
    enable_fuzzy_lookup: bool = True


@dataclass(slots=True)
class AppConfig:
    """Top level configuration container that can be expanded later."""

    capture: CaptureConfig = field(default_factory=CaptureConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    dictionary: DictionaryConfig = field(default_factory=DictionaryConfig)


__all__ = ["AppConfig", "CaptureConfig", "OverlayConfig", "DictionaryConfig"]
