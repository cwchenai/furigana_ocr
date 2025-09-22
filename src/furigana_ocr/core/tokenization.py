"""Tokenisation utilities built around :mod:`fugashi`."""

from __future__ import annotations

from typing import List

try:  # pragma: no cover - the dependency may be missing in CI
    from fugashi import Tagger
except Exception:  # pragma: no cover - fallback mode
    Tagger = None  # type: ignore

from .models import TokenData


class Tokenizer:
    """Tokenise Japanese text into morphological units."""

    def __init__(self, dictionary: str | None = None) -> None:
        self._tagger = None
        if Tagger is None:
            return
        try:
            self._tagger = Tagger(dict=dictionary) if dictionary else Tagger()
        except Exception:
            self._tagger = None

    def tokenize(self, text: str) -> List[TokenData]:
        if not text:
            return []
        if self._tagger is None:
            return [TokenData(surface=chunk) for chunk in text.strip().split() if chunk]

        tokens: List[TokenData] = []
        for word in self._tagger(text):
            lemma = getattr(word, "dictionary_form", None) or getattr(word, "lemma", None)
            if lemma:
                lemma = str(lemma)
            pos = self._extract_pos(word)
            reading = getattr(word, "feature", None)
            if isinstance(reading, (list, tuple)) and reading:
                reading_text = reading[0]
            else:
                reading_text = getattr(word, "reading", None)
            tokens.append(
                TokenData(
                    surface=str(getattr(word, "surface", "")),
                    reading=str(reading_text) if reading_text else None,
                    lemma=lemma,
                    part_of_speech=pos,
                )
            )
        return tokens

    @staticmethod
    def _extract_pos(word) -> str | None:
        features = getattr(word, "feature", None)
        if isinstance(features, (list, tuple)) and len(features) > 1:
            return "-".join(str(item) for item in features[1:4] if item)
        pos = getattr(word, "pos", None)
        if isinstance(pos, str):
            return pos
        return None


__all__ = ["Tokenizer"]
