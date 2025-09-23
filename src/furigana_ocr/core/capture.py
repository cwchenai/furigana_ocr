"""Screen capture utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import mss
from PIL import Image

from .models import Region


@dataclass
class ScreenCapture:
    """Encapsulates monitor capture using :mod:`mss`."""

    monitor_index: int = 0

    def __post_init__(self) -> None:
        self._mss: Optional[mss.mss] = None

    def _ensure_session(self) -> mss.mss:
        if self._mss is None:
            self._mss = mss.mss()
        return self._mss

    def capture(self, region: Region) -> Image.Image:
        """Capture the supplied region and return a PIL image."""
        import mss
        if region is None:
            raise ValueError("A capture region must be selected before starting the pipeline.")

        left, top, width, height = region
        monitor = {"left": left, "top": top, "width": width, "height": height}
        with mss.mss() as mss:
            raw = mss.grab(monitor)
            
        return Image.frombytes("RGB", raw.size, raw.rgb)

    def close(self) -> None:
        if self._mss is not None:
            self._mss.close()
            self._mss = None


__all__ = ["ScreenCapture"]
