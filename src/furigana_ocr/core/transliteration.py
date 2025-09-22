"""Furigana generation helpers."""

from __future__ import annotations

from typing import Iterable, List, Optional

from pykakasi import kakasi


class FuriganaGenerator:
    """Generate Hiragana readings for Japanese text using :mod:`pykakasi`."""

    def __init__(self) -> None:
        self._kakasi = kakasi()
        self._kakasi.setMode("J", "H")  # Kanji to Hiragana
        self._kakasi.setMode("K", "H")  # Katakana to Hiragana

    def convert(self, text: str) -> List[str]:
        return [entry["hira"] for entry in self._kakasi.convert(text)]

    def reading_for(self, text: str) -> Optional[str]:
        if not text:
            return None
        try:
            parts = self._kakasi.convert(text)
        except Exception:  # pragma: no cover - defensive fallback
            return None
        readings = [part.get("hira") for part in parts if part.get("hira")]
        if not readings:
            return None
        return "".join(readings)

    def annotate_tokens(self, tokens: Iterable[str]) -> List[Optional[str]]:
        return [self.reading_for(token) for token in tokens]


__all__ = ["FuriganaGenerator"]
