"""Screen capture utilities."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import mss
from PIL import Image

from .models import Region


@dataclass
class ScreenCapture:
    """Encapsulates monitor capture using :mod:`mss`."""

    monitor_index: int = 0
    mask_color: Tuple[int, int, int] = (255, 255, 255)

    def __post_init__(self) -> None:
        self._mss: Optional[mss.mss] = None
        self._lock = threading.Lock()
        self._mask_regions: List[Region] = []

    def _ensure_session(self) -> mss.mss:
        if self._mss is None:
            self._mss = mss.mss()
        return self._mss

    def set_mask_regions(self, regions: Sequence[Region]) -> None:
        """Update rectangles that should be blanked out in future captures."""

        valid: List[Region] = []
        for region in regions:
            left, top, width, height = region
            if width <= 0 or height <= 0:
                continue
            valid.append((int(left), int(top), int(width), int(height)))
        with self._lock:
            self._mask_regions = valid

    def _get_mask_regions(self) -> List[Region]:
        with self._lock:
            return list(self._mask_regions)

    def capture(self, region: Region) -> Image.Image:
        """Capture the supplied region and return a PIL image."""
        import mss
        if region is None:
            raise ValueError("A capture region must be selected before starting the pipeline.")

        left, top, width, height = region
        monitor = {"left": left, "top": top, "width": width, "height": height}
        with mss.mss() as mss:
            raw = mss.grab(monitor)

        image = Image.frombytes("RGB", raw.size, raw.rgb)
        masks = self._get_mask_regions()
        if masks:
            self._apply_masks(image, region, masks, self.mask_color)
        return image

    def close(self) -> None:
        if self._mss is not None:
            self._mss.close()
            self._mss = None

    @staticmethod
    def intersect_regions(a: Region, b: Region) -> Region | None:
        """Return the intersection between two regions, if any."""

        a_left, a_top, a_width, a_height = a
        b_left, b_top, b_width, b_height = b
        left = max(a_left, b_left)
        top = max(a_top, b_top)
        right = min(a_left + a_width, b_left + b_width)
        bottom = min(a_top + a_height, b_top + b_height)
        if right <= left or bottom <= top:
            return None
        return (left, top, right - left, bottom - top)

    @staticmethod
    def _apply_masks(
        image: Image.Image,
        capture_region: Region,
        masks: Sequence[Region],
        fill: Tuple[int, int, int],
    ) -> None:
        """Overlay ``fill`` rectangles over the capture ``image`` for every mask."""

        capture_left, capture_top, _, _ = capture_region
        for mask in masks:
            intersection = ScreenCapture.intersect_regions(capture_region, mask)
            if intersection is None:
                continue
            left, top, width, height = intersection
            if width <= 0 or height <= 0:
                continue
            local_left = left - capture_left
            local_top = top - capture_top
            box = (
                local_left,
                local_top,
                local_left + width,
                local_top + height,
            )
            image.paste(fill, box)


__all__ = ["ScreenCapture"]
