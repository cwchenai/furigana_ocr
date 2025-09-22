"""Core domain services for capturing, recognising and annotating text."""

from .capture import ScreenCapture
from .dictionary import DictionaryLookup
from .models import (
    BoundingBox,
    DictionaryEntry,
    OCRResult,
    OCRWord,
    Region,
    TokenAnnotation,
    TokenData,
)
from .ocr import OCRProcessor
from .tokenization import Tokenizer
from .transliteration import FuriganaGenerator

__all__ = [
    "BoundingBox",
    "DictionaryEntry",
    "DictionaryLookup",
    "FuriganaGenerator",
    "OCRProcessor",
    "OCRResult",
    "OCRWord",
    "Region",
    "ScreenCapture",
    "TokenAnnotation",
    "TokenData",
    "Tokenizer",
]
