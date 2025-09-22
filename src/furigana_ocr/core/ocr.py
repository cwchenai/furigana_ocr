"""OCR processing using Tesseract."""

from __future__ import annotations

from typing import List

import pytesseract
from pytesseract import Output

from .models import BoundingBox, OCRResult, OCRWord


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

    def run(self, image) -> OCRResult:
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


__all__ = ["OCRProcessor"]
