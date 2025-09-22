"""Dictionary lookup helpers built on top of :mod:`jamdict`."""

from __future__ import annotations

from typing import List, Sequence

try:  # pragma: no cover - optional dependency in tests
    from jamdict import Jamdict
except Exception:  # pragma: no cover - fallback mode
    Jamdict = None  # type: ignore

from .models import DictionaryEntry


class DictionaryLookup:
    """Perform dictionary lookups and normalise the results."""

    def __init__(self, search_limit: int = 3, enable_fuzzy_lookup: bool = True) -> None:
        self.search_limit = search_limit
        self.enable_fuzzy_lookup = enable_fuzzy_lookup
        try:
            self._jamdict = Jamdict() if Jamdict else None
        except Exception:
            self._jamdict = None

    def lookup(self, surface: str) -> List[DictionaryEntry]:
        if not surface:
            return []
        if self._jamdict is None:
            return []
        try:
            result = self._jamdict.lookup(surface, strict=not self.enable_fuzzy_lookup)
        except Exception:  # pragma: no cover - defensive fallback
            return []
        entries: List[DictionaryEntry] = []
        for entry in getattr(result, "entries", [])[: self.search_limit]:
            entries.append(
                DictionaryEntry(
                    expression=self._extract_expression(entry),
                    reading=self._extract_reading(entry),
                    senses=self._extract_glosses(entry),
                )
            )
        return entries

    @staticmethod
    def _extract_expression(entry) -> str:
        kanji_forms = getattr(entry, "kanji_forms", None)
        if kanji_forms:
            text = getattr(kanji_forms[0], "text", None)
            if text:
                return str(text)
        reading_forms = getattr(entry, "reading_forms", None)
        if reading_forms:
            text = getattr(reading_forms[0], "text", None)
            if text:
                return str(text)
        return str(getattr(entry, "idseq", ""))

    @staticmethod
    def _extract_reading(entry) -> str | None:
        reading_forms = getattr(entry, "reading_forms", None)
        if reading_forms:
            text = getattr(reading_forms[0], "text", None)
            if text:
                return str(text)
        return None

    @staticmethod
    def _extract_glosses(entry) -> Sequence[str]:
        senses = getattr(entry, "senses", None)
        glosses: List[str] = []
        if not senses:
            return glosses
        for sense in senses:
            for gloss in getattr(sense, "gloss", []) or []:
                text = getattr(gloss, "text", None)
                if text:
                    glosses.append(str(text))
        return glosses


__all__ = ["DictionaryLookup"]
