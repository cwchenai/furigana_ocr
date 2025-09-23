"""Geometry utilities shared between modules."""

from __future__ import annotations

from typing import Iterable, Tuple

from ..core.models import BoundingBox, OCRWord, Region


def region_from_bbox(box: BoundingBox) -> Region:
    return box.to_tuple()


def combine_bounding_boxes(boxes: Iterable[BoundingBox]) -> BoundingBox:
    points = []
    for box in boxes:
        points.extend(
            [
                (box.left, box.top),
                (box.right, box.top),
                (box.left, box.bottom),
                (box.right, box.bottom),
            ]
        )
    if not points:
        return BoundingBox(0, 0, 0, 0)
    return BoundingBox.from_points(points)


def segment_ocr_word(word: OCRWord, start: int, length: int) -> Tuple[str, BoundingBox]:
    """Return a sub-section of ``word`` using approximate geometric splits.

    The helper operates on the number of non-whitespace characters in the
    ``OCRWord``.  The provided ``start`` and ``length`` arguments are measured in
    those units.  The function computes an average character width/height and
    uses it to derive a bounding box that approximates the requested substring.
    """

    non_ws_chars = [ch for ch in word.text if not ch.isspace()]
    total = len(non_ws_chars)
    if total == 0 or length <= 0 or start >= total:
        return "", BoundingBox(word.bbox.left, word.bbox.top, 0, 0)

    start = max(0, start)
    end = min(start + length, total)
    if end <= start:
        return "", BoundingBox(word.bbox.left, word.bbox.top, 0, 0)

    text = "".join(non_ws_chars[start:end])

    horizontal = word.bbox.width >= word.bbox.height
    if horizontal:
        start_pos = word.bbox.left + round(word.bbox.width * start / total)
        end_pos = word.bbox.left + round(word.bbox.width * end / total)
        left = min(start_pos, word.bbox.right)
        right = min(max(end_pos, left + 1), word.bbox.right)
        width = max(1, right - left)
        bbox = BoundingBox(left, word.bbox.top, width, word.bbox.height)
    else:
        start_pos = word.bbox.top + round(word.bbox.height * start / total)
        end_pos = word.bbox.top + round(word.bbox.height * end / total)
        top = min(start_pos, word.bbox.bottom)
        bottom = min(max(end_pos, top + 1), word.bbox.bottom)
        height = max(1, bottom - top)
        bbox = BoundingBox(word.bbox.left, top, word.bbox.width, height)

    return text, bbox


__all__ = ["combine_bounding_boxes", "region_from_bbox", "segment_ocr_word"]
