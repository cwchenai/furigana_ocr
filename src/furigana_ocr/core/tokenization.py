"""Tokenisation utilities built around :mod:`fugashi`."""

from __future__ import annotations

from typing import List, Sequence

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
            reading_text = self._extract_reading(word)
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

    @staticmethod
    def _extract_reading(word) -> str | None:
        reading = getattr(word, "reading", None)
        if isinstance(reading, str) and reading:
            return reading
        for attr in ("pron", "pronunciation", "kana"):
            value = getattr(word, attr, None)
            if isinstance(value, str) and value:
                return value
        features = getattr(word, "feature", None)
        if features is None:
            return None
        for attr in ("reading", "kana", "pron", "pronunciation"):
            value = getattr(features, attr, None)
            if isinstance(value, str) and value:
                return value
        if isinstance(features, str):
            parts = [part.strip() for part in features.split(",")]
            candidate = Tokenizer._pick_reading_candidate(parts)
            if candidate:
                return candidate
        if isinstance(features, Sequence):
            candidate = Tokenizer._pick_reading_candidate(features)
            if candidate:
                return candidate
            for value in features:
                if not value:
                    continue
                text = str(value).strip()
                if not text or text == "*":
                    continue
                if any("ぁ" <= ch <= "ゖ" or "ァ" <= ch <= "ヺ" for ch in text):
                    return text
        return None

    @staticmethod
    def _pick_reading_candidate(features: Sequence) -> str | None:
        reading_indexes = (7, 8, 9, 10, 11)
        for index in reading_indexes:
            if index >= len(features):
                break
            value = features[index]
            if not value:
                continue
            text = str(value).strip()
            if not text or text == "*":
                continue
            if any("ぁ" <= ch <= "ゖ" or "ァ" <= ch <= "ヺ" for ch in text):
                return text
        return None


__all__ = ["Tokenizer"]
