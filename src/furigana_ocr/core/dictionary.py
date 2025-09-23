"""Dictionary lookup helpers built on top of :mod:`jamdict`."""

from __future__ import annotations

import threading
from typing import Any, List, Sequence

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
        self._thread_local = threading.local()
        self._initialisation_failed = False

    def lookup(self, surface: str) -> List[DictionaryEntry]:
        if not surface:
            return []
        client = self._get_client()
        if client is None:
            return []
        try:
            result = client.lookup(surface, strict=not self.enable_fuzzy_lookup)
        except AttributeError as exc:  # pragma: no cover - defensive fallback
            # ``Jamdict`` stores DB handles on a thread local object.  When the
            # instance created in one thread is re-used from another thread the
            # attribute access can fail with ``_thread._local`` errors.  Reset the
            # client for the current thread and retry once.
            if "_thread._local" not in str(exc):
                return []
            self._reset_client()
            client = self._get_client()
            if client is None:
                return []
            try:
                result = client.lookup(surface, strict=not self.enable_fuzzy_lookup)
            except Exception:
                return []
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

    def _get_client(self) -> Any | None:
        if self._initialisation_failed or Jamdict is None:
            return None
        client = getattr(self._thread_local, "jamdict", None)
        if client is not None:
            return client
        try:
            client = Jamdict()
        except Exception:
            self._initialisation_failed = True
            return None
        self._thread_local.jamdict = client
        return client

    def _reset_client(self) -> None:
        if hasattr(self._thread_local, "jamdict"):
            delattr(self._thread_local, "jamdict")

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
