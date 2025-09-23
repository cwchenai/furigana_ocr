"""Core domain services for capturing, recognising and annotating text."""

from __future__ import annotations

from importlib import import_module
from typing import Any

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


def __getattr__(name: str) -> Any:  # pragma: no cover - thin lazy import layer
    if name in __all__:
        module_map = {
            "ScreenCapture": "capture",
            "DictionaryLookup": "dictionary",
            "Tokenizer": "tokenization",
            "FuriganaGenerator": "transliteration",
            "OCRProcessor": "ocr",
            "BoundingBox": "models",
            "DictionaryEntry": "models",
            "OCRResult": "models",
            "OCRWord": "models",
            "Region": "models",
            "TokenAnnotation": "models",
            "TokenData": "models",
        }
        module_name = module_map[name]
        module = import_module(f"{__name__}.{module_name}")
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:  # pragma: no cover - aids interactive use
    return sorted(__all__ + list(globals().keys()))
