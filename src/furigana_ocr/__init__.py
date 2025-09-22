"""Top-level package for the Furigana OCR overlay application."""

from importlib import metadata


def __getattr__(name: str) -> str:
    if name == "__version__":
        try:
            return metadata.version("furigana-ocr")
        except metadata.PackageNotFoundError:  # pragma: no cover - used during development
            return "0.0.0"
    raise AttributeError(name)


__all__ = ["__version__"]
