"""Tests for the processing pipeline orchestration layer."""

from __future__ import annotations

import sys
import types
from typing import List


if "PIL" not in sys.modules:  # pragma: no cover - test isolation shim
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")

    class _Image:  # minimal stand-in to satisfy type hints
        pass

    image_module.Image = _Image
    pil_module.Image = image_module
    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = image_module

if "mss" not in sys.modules:  # pragma: no cover - test isolation shim
    mss_module = types.ModuleType("mss")

    class _MSS:  # minimal stub used for type checking
        def __enter__(self):  # pragma: no cover - defensive default
            return self

        def __exit__(self, exc_type, exc, tb):  # pragma: no cover - defensive default
            return False

        def grab(self, monitor):  # pragma: no cover - not used in test
            raise NotImplementedError

        def close(self):  # pragma: no cover - defensive default
            return None

    mss_module.mss = _MSS
    sys.modules["mss"] = mss_module

if "pytesseract" not in sys.modules:  # pragma: no cover - test isolation shim
    pytesseract_module = types.ModuleType("pytesseract")

    class _PytesseractInner:
        tesseract_cmd = ""

    def _image_to_data(*args, **kwargs):  # pragma: no cover - not used in test
        raise NotImplementedError

    pytesseract_module.pytesseract = _PytesseractInner()
    pytesseract_module.image_to_data = _image_to_data
    pytesseract_module.Output = types.SimpleNamespace(DICT="DICT")
    sys.modules["pytesseract"] = pytesseract_module

if "pykakasi" not in sys.modules:  # pragma: no cover - test isolation shim
    pykakasi_module = types.ModuleType("pykakasi")

    class _Converter:
        def do(self, text):  # pragma: no cover - not used in test
            return text

    class _Kakasi:
        def setMode(self, *args, **kwargs):  # pragma: no cover - defensive default
            return None

        def getConverter(self):  # pragma: no cover - defensive default
            return _Converter()

    def _kakasi():  # pragma: no cover - defensive default
        return _Kakasi()

    pykakasi_module.kakasi = _kakasi
    sys.modules["pykakasi"] = pykakasi_module

from furigana_ocr.config import AppConfig
from furigana_ocr.core.models import (
    BoundingBox,
    DictionaryEntry,
    OCRResult,
    OCRWord,
    TokenData,
)
from furigana_ocr.services.pipeline import PipelineDependencies, ProcessingPipeline


class _DummyCapture:
    def capture(self, region):  # pragma: no cover - not used in test
        raise NotImplementedError


class _DummyOCR:
    def run(self, image):  # pragma: no cover - not used in test
        raise NotImplementedError


class _DummyTokenizer:
    def tokenize(self, text: str) -> List[TokenData]:  # pragma: no cover - not used in test
        return []


class _DummyFurigana:
    def reading_for(self, surface: str):  # pragma: no cover - not used in test
        return None


class _DummyDictionary:
    def lookup(self, surface: str):  # pragma: no cover - not used in test
        return []


class _RecordingDictionary:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls: List[str] = []

    def lookup(self, surface: str):
        self.calls.append(surface)
        return self.mapping.get(surface, [])


def _build_pipeline() -> ProcessingPipeline:
    config = AppConfig()
    deps = PipelineDependencies(
        capture=_DummyCapture(),
        ocr=_DummyOCR(),
        tokenizer=_DummyTokenizer(),
        furigana=_DummyFurigana(),
        dictionary=_DummyDictionary(),
    )
    return ProcessingPipeline(config, deps=deps)


def test_match_words_returns_bounding_boxes_for_substrings() -> None:
    pipeline = _build_pipeline()
    word = OCRWord(
        text="今天天氣真好",
        confidence=85.0,
        bbox=BoundingBox(left=10, top=20, width=120, height=30),
        order=0,
    )
    ocr_result = OCRResult(text="今天天氣真好", words=[word])
    tokens = [
        TokenData(surface="今天"),
        TokenData(surface="天氣"),
        TokenData(surface="真好"),
    ]

    annotations = pipeline._enrich(tokens, ocr_result)

    assert [annotation.token.surface for annotation in annotations] == [
        "今天",
        "天氣",
        "真好",
    ]
    for annotation in annotations:
        assert annotation.bbox is not None
        assert annotation.bbox.width > 0
        assert annotation.bbox.height > 0


class _MappingFurigana:
    def __init__(self, mapping):
        self._mapping = mapping

    def reading_for(self, surface: str):
        return self._mapping.get(surface)


def test_furigana_normalises_katakana_reading_to_hiragana() -> None:
    pipeline = _build_pipeline()
    pipeline.furigana = _MappingFurigana({"サンプル": "さんぷる"})
    word = OCRWord(
        text="漢字",
        confidence=90.0,
        bbox=BoundingBox(left=0, top=0, width=10, height=10),
        order=0,
    )
    token = TokenData(surface="漢字", reading="サンプル")

    annotations = pipeline._enrich([token], OCRResult(text="漢字", words=[word]))

    assert annotations[0].furigana == "さんぷる"


def test_furigana_skips_annotation_for_existing_kana_surface() -> None:
    pipeline = _build_pipeline()
    pipeline.furigana = _MappingFurigana({"テスト": "てすと"})
    word = OCRWord(
        text="テスト",
        confidence=88.0,
        bbox=BoundingBox(left=0, top=0, width=12, height=12),
        order=0,
    )
    token = TokenData(surface="テスト", reading="テスト")

    annotations = pipeline._enrich([token], OCRResult(text="テスト", words=[word]))

    assert annotations[0].furigana is None


def test_dictionary_lookup_falls_back_to_lemma() -> None:
    pipeline = _build_pipeline()
    entry = DictionaryEntry(expression="走る", reading=None, senses=("to run",))
    dictionary = _RecordingDictionary({"走る": [entry]})
    pipeline.dictionary = dictionary
    token = TokenData(surface="走った", lemma="走る")

    annotations = pipeline._enrich([token], OCRResult(text="走った", words=[]))

    assert dictionary.calls == ["走った", "走る"]
    assert annotations[0].dictionary_entries == [entry]
