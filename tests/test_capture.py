from __future__ import annotations

import sys
import types

if "PIL" not in sys.modules:  # pragma: no cover - test isolation shim
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")

    class _Image:  # pragma: no cover - minimal stub for type hints
        @staticmethod
        def frombytes(*args, **kwargs):
            raise NotImplementedError

    image_module.Image = _Image
    pil_module.Image = image_module
    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = image_module

if "mss" not in sys.modules:  # pragma: no cover - test isolation shim
    mss_module = types.ModuleType("mss")

    class _MSS:  # pragma: no cover - not used directly in tests
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def grab(self, monitor):
            raise NotImplementedError

        def close(self):
            return None

    mss_module.mss = _MSS
    sys.modules["mss"] = mss_module

from furigana_ocr.core.capture import ScreenCapture


class _DummyImage:
    def __init__(self, width: int, height: int, color: tuple[int, int, int]) -> None:
        self._width = width
        self._height = height
        self._pixels = [
            [color for _ in range(width)]
            for _ in range(height)
        ]

    def paste(self, color: tuple[int, int, int], box) -> None:
        left, top, right, bottom = box
        for y in range(max(top, 0), min(bottom, self._height)):
            for x in range(max(left, 0), min(right, self._width)):
                self._pixels[y][x] = color

    def getpixel(self, pos: tuple[int, int]) -> tuple[int, int, int]:
        x, y = pos
        return self._pixels[y][x]


def test_intersect_regions_returns_overlap() -> None:
    first = (10, 20, 80, 60)
    second = (40, 40, 50, 50)

    assert ScreenCapture.intersect_regions(first, second) == (40, 40, 50, 40)


def test_intersect_regions_without_overlap_returns_none() -> None:
    first = (0, 0, 10, 10)
    second = (20, 20, 5, 5)

    assert ScreenCapture.intersect_regions(first, second) is None


def test_apply_masks_whitens_intersection_area() -> None:
    image = _DummyImage(100, 100, (0, 0, 0))
    capture_region = (10, 10, 100, 100)
    masks = [(20, 20, 30, 30)]

    ScreenCapture._apply_masks(image, capture_region, masks, (255, 255, 255))

    assert image.getpixel((5, 5)) == (0, 0, 0)
    assert image.getpixel((25, 25)) == (255, 255, 255)
    assert image.getpixel((35, 35)) == (255, 255, 255)
    assert image.getpixel((60, 60)) == (0, 0, 0)
