"""High level orchestration of the OCR -> tokenisation -> dictionary pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from PIL import Image

from ..config import AppConfig
from ..core.capture import ScreenCapture
from ..core.dictionary import DictionaryLookup
from ..core.models import OCRResult, OCRWord, Region, TokenAnnotation, TokenData
from ..core.ocr import OCRProcessor
from ..core.tokenization import Tokenizer
from ..core.transliteration import FuriganaGenerator
from ..utils import combine_bounding_boxes


@dataclass
class PipelineDependencies:
    """Convenience container for the collaborating services."""

    capture: ScreenCapture
    ocr: OCRProcessor
    tokenizer: Tokenizer
    furigana: FuriganaGenerator
    dictionary: DictionaryLookup


class ProcessingPipeline:
    """Coordinates the individual processing components."""

    def __init__(self, config: AppConfig, deps: PipelineDependencies | None = None) -> None:
        self.config = config
        self.capture = deps.capture if deps else ScreenCapture()
        self.ocr = deps.ocr if deps else OCRProcessor(
            language=config.capture.language,
            psm=config.capture.psm,
            oem=config.capture.oem,
            tesseract_cmd=str(config.capture.tesseract_cmd) if config.capture.tesseract_cmd else None,
        )
        self.tokenizer = deps.tokenizer if deps else Tokenizer()
        self.furigana = deps.furigana if deps else FuriganaGenerator()
        self.dictionary = deps.dictionary if deps else DictionaryLookup(
            search_limit=config.dictionary.search_limit,
            enable_fuzzy_lookup=config.dictionary.enable_fuzzy_lookup,
        )

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
        for token in tokens:
            matched_words, word_index = self._match_words(token.surface, words, word_index)
            if matched_words:
                bbox = combine_bounding_boxes(word.bbox for word in matched_words)
                confidence = sum(word.confidence for word in matched_words) / len(matched_words)
            else:
                bbox = None
                confidence = 0.0
            furigana = token.reading or self.furigana.reading_for(token.surface)
            dictionary_entries = self.dictionary.lookup(token.surface)
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
        self, surface: str, words: Sequence[OCRWord], start_index: int
    ) -> tuple[List[OCRWord], int]:
        if start_index >= len(words):
            return [], start_index
        cleaned = surface.strip()
        if not cleaned:
            word = words[start_index]
            return [word], start_index + 1
        collected: List[OCRWord] = []
        combined = ""
        index = start_index
        while index < len(words):
            word = words[index]
            index += 1
            if not word.text.strip():
                continue
            collected.append(word)
            combined += word.text
            combined_clean = combined.strip()
            if cleaned in combined_clean or combined_clean.endswith(cleaned):
                break
            if len(combined_clean) >= len(cleaned):
                break
        if not collected:
            return [], index
        return collected, index


__all__ = ["PipelineDependencies", "ProcessingPipeline"]
