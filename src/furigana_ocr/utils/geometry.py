"""Geometry utilities shared between modules."""

from __future__ import annotations

from typing import Iterable, Tuple

from ..core.models import BoundingBox, Region


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


__all__ = ["combine_bounding_boxes", "region_from_bbox"]
