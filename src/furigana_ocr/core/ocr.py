"""OCR processing backends."""

from __future__ import annotations

from typing import List, Protocol

import pytesseract
from PIL import Image
from pytesseract import Output

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency import guard
    np = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency import guard
    from paddleocr import PaddleOCR as _PaddleOCR
except ImportError:  # pragma: no cover - optional dependency import guard
    _PaddleOCR = None

from .models import BoundingBox, OCRResult, OCRWord


class BaseOCRProcessor(Protocol):
    """Common interface for OCR processors."""

    def run(self, image: Image.Image) -> OCRResult:
        """Execute OCR over ``image`` and return the parsed response."""


class OCRProcessor:
    """Wraps :func:`pytesseract.image_to_data` and normalises the output."""

    def __init__(self, language: str, psm: int, oem: int, tesseract_cmd: str | None = None) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)
        self.language = language
        self.psm = psm
        self.oem = oem

    def _build_config(self) -> str:
        return f"--psm {self.psm} --oem {self.oem}"

    def run(self, image: Image.Image) -> OCRResult:
        """Execute Tesseract over a PIL image and return the parsed response."""

        data = pytesseract.image_to_data(
            image,
            lang=self.language,
            config=self._build_config(),
            output_type=Output.DICT,
        )
        words = self._parse_words(data)
        text = "".join(word.text for word in words)
        return OCRResult(text=text, words=words)

    def _parse_words(self, data: dict) -> List[OCRWord]:
        words: List[OCRWord] = []
        for index, text in enumerate(data.get("text", [])):
            text = text.strip()
            if not text:
                continue
            conf_value = data.get("conf", ["0"])  # pytesseract returns strings
            try:
                confidence = float(conf_value[index])
            except (ValueError, IndexError):
                confidence = 0.0
            box = BoundingBox(
                left=int(data.get("left", [0])[index]),
                top=int(data.get("top", [0])[index]),
                width=int(data.get("width", [0])[index]),
                height=int(data.get("height", [0])[index]),
            )
            words.append(OCRWord(text=text, confidence=confidence, bbox=box, order=len(words)))
        return words


class PaddleOCRProcessor:
    """OCR backend powered by `PaddleOCR <https://github.com/PaddlePaddle/PaddleOCR>`_."""

    def __init__(self, language: str) -> None:
        if _PaddleOCR is None:  # pragma: no cover - defensive guard
            raise RuntimeError(
                "PaddleOCR is not installed; please install paddleocr to use this engine."
            )
        self.language = language
        self._ocr = _PaddleOCR(
            lang=self._normalise_language(language),
            show_log=False,
            use_angle_cls=False,
        )

    def _normalise_language(self, language: str) -> str:
        mapping = {
            "jpn": "japan",
            "jpn_vert": "japan_vert",
        }
        return mapping.get(language, language)

    def run(self, image: Image.Image) -> OCRResult:
        pil_image = image.convert("RGB") if image.mode != "RGB" else image
        if np is None:  # pragma: no cover - defensive guard
            raise RuntimeError(
                "NumPy is required for the PaddleOCR engine; please install numpy."
            )
        np_image = np.array(pil_image)
        result = self._ocr.ocr(np_image, cls=False)

        if not result:
            detections = []
        elif len(result) == 1 and isinstance(result[0], list):
            detections = result[0]
        else:
            detections = result
        words: List[OCRWord] = []
        text_parts: List[str] = []

        for entry in detections:
            if not entry or len(entry) < 2:
                continue
            box_points, (word_text, score) = entry
            if not word_text:
                continue
            xs = [point[0] for point in box_points]
            ys = [point[1] for point in box_points]
            left = int(min(xs))
            top = int(min(ys))
            width = int(max(xs) - left)
            height = int(max(ys) - top)
            box = BoundingBox(left=left, top=top, width=width, height=height)
            confidence = float(score) * 100.0
            words.append(OCRWord(text=word_text, confidence=confidence, bbox=box, order=len(words)))
            text_parts.append(word_text)

        text = "".join(text_parts)
        return OCRResult(text=text, words=words)


__all__ = ["BaseOCRProcessor", "OCRProcessor", "PaddleOCRProcessor"]
