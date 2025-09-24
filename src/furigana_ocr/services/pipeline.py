"""High level orchestration of the OCR -> tokenisation -> dictionary pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from PIL import Image

from ..config import AppConfig
from ..core.capture import ScreenCapture
from ..core.dictionary import DictionaryLookup
from ..core.models import OCRResult, OCRWord, Region, TokenAnnotation, TokenData
from ..core.ocr import BaseOCRProcessor, OCRProcessor, PaddleOCRProcessor
from ..core.tokenization import Tokenizer
from ..core.transliteration import FuriganaGenerator
from ..utils import combine_bounding_boxes, segment_ocr_word


@dataclass
class PipelineDependencies:
    """Convenience container for the collaborating services."""

    capture: ScreenCapture
    ocr: BaseOCRProcessor
    tokenizer: Tokenizer
    furigana: FuriganaGenerator
    dictionary: DictionaryLookup


class ProcessingPipeline:
    """Coordinates the individual processing components."""

    def __init__(self, config: AppConfig, deps: PipelineDependencies | None = None) -> None:
        self.config = config
        self.capture = deps.capture if deps else ScreenCapture()
        self.ocr = deps.ocr if deps else self._build_ocr_processor(config.capture.engine)
        self.tokenizer = deps.tokenizer if deps else Tokenizer()
        self.furigana = deps.furigana if deps else FuriganaGenerator()
        self.dictionary = deps.dictionary if deps else DictionaryLookup(
            search_limit=config.dictionary.search_limit,
            enable_fuzzy_lookup=config.dictionary.enable_fuzzy_lookup,
        )

    def _build_ocr_processor(self, engine: str) -> BaseOCRProcessor:
        engine = engine.lower()
        capture_cfg = self.config.capture
        if engine == "paddle":
            return PaddleOCRProcessor(language=capture_cfg.language)
        return OCRProcessor(
            language=capture_cfg.language,
            psm=capture_cfg.psm,
            oem=capture_cfg.oem,
            tesseract_cmd=str(capture_cfg.tesseract_cmd) if capture_cfg.tesseract_cmd else None,
        )

    def set_ocr_engine(self, engine: str) -> None:
        """Switch the underlying OCR implementation at runtime."""

        self.config.capture.engine = engine
        self.ocr = self._build_ocr_processor(engine)

    def process_region(self, region: Region) -> List[TokenAnnotation]:
        image = self.capture.capture(region)
        return self.process_image(image)

    def process_image(self, image: Image.Image) -> List[TokenAnnotation]:
        ocr_result = self.ocr.run(image)
        tokens = self.tokenizer.tokenize(ocr_result.text)
        return self._enrich(tokens, ocr_result)

    def _enrich(self, tokens: Sequence[TokenData], ocr_result: OCRResult) -> List[TokenAnnotation]:
        annotations: List[TokenAnnotation] = []
        words = ocr_result.words
        word_index = 0
        char_offset = 0
        for token in tokens:
            matched_words, word_index, char_offset = self._match_words(
                token.surface, words, word_index, char_offset
            )
            if matched_words:
                bbox = combine_bounding_boxes(word.bbox for word in matched_words)
                confidence = sum(word.confidence for word in matched_words) / len(matched_words)
            else:
                bbox = None
                confidence = 0.0
            furigana = self._normalize_furigana(token.reading)
            if furigana is None:
                furigana = self._normalize_furigana(self.furigana.reading_for(token.surface))
            if furigana and self._is_kana_text(token.surface):
                furigana = None
            dictionary_entries = self.dictionary.lookup(token.surface)
            if (
                not dictionary_entries
                and token.lemma
                and token.lemma.strip()
                and token.lemma.strip() != token.surface.strip()
            ):
                dictionary_entries = self.dictionary.lookup(token.lemma.strip())
            annotations.append(
                TokenAnnotation(
                    token=token,
                    furigana=furigana,
                    bbox=bbox,
                    confidence=confidence,
                    dictionary_entries=dictionary_entries,
                )
            )
        return annotations

    def _match_words(
        self,
        surface: str,
        words: Sequence[OCRWord],
        start_index: int,
        start_offset: int,
    ) -> tuple[List[OCRWord], int, int]:
        if start_index >= len(words):
            return [], start_index, start_offset

        cleaned = surface.strip()
        if not cleaned:
            return [], start_index, start_offset

        collected: List[OCRWord] = []
        index = start_index
        offset = start_offset
        remaining = cleaned

        while index < len(words) and remaining:
            word = words[index]
            compact = "".join(ch for ch in word.text if not ch.isspace())
            if not compact:
                index += 1
                offset = 0
                continue
            if offset >= len(compact):
                index += 1
                offset = 0
                continue

            available = compact[offset:]
            if not available:
                index += 1
                offset = 0
                continue

            if remaining.startswith(available):
                length = len(available)
            elif available.startswith(remaining):
                length = len(remaining)
            else:
                length = 0
                for a, b in zip(remaining, available):
                    if a != b:
                        break
                    length += 1
            if length <= 0:
                break

            text, bbox = segment_ocr_word(word, offset, length)
            if text:
                collected.append(
                    OCRWord(text=text, confidence=word.confidence, bbox=bbox, order=word.order)
                )

            remaining = remaining[length:]
            offset += length
            if offset >= len(compact):
                index += 1
                offset = 0

        if not collected:
            return [], index, offset
        return collected, index, offset

    def _normalize_furigana(self, text: str | None) -> str | None:
        if not text:
            return None
        candidate = text.strip()
        if not candidate:
            return None
        converted = self.furigana.reading_for(candidate)
        if converted:
            normalized = converted.strip()
            if normalized:
                return normalized
        return candidate

    @staticmethod
    def _is_kana_text(text: str) -> bool:
        if not text:
            return False
        has_kana = False
        for char in text:
            if char.isspace():
                continue
            if ProcessingPipeline._is_kana_char(char):
                has_kana = True
                continue
            return False
        return has_kana

    @staticmethod
    def _is_kana_char(char: str) -> bool:
        if not char:
            return False
        if "ぁ" <= char <= "ゖ":
            return True
        if "ァ" <= char <= "ヺ":
            return True
        if char in {"ゝ", "ゞ", "ヽ", "ヾ", "ー", "・"}:
            return True
        return False


__all__ = ["PipelineDependencies", "ProcessingPipeline"]
