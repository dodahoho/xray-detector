from __future__ import annotations

from xray_detector.models import Detection
from xray_detector.util.geometry import (
    box_area,
    box_iou,
    clamp_box,
    detection_to_coco,
    detection_to_yolo,
    xywh_to_xyxy,
    xyxy_to_xywh,
)


def test_xy_conversions() -> None:
    assert xyxy_to_xywh(10, 20, 40, 60) == (10, 20, 30, 40)
    assert xywh_to_xyxy(10, 20, 30, 40) == (10, 20, 40, 60)
    assert box_area(0, 0, 10, 5) == 50


def test_clamp_box_keeps_box_inside_image() -> None:
    assert clamp_box(-10, -5, 120, 90, 100, 80) == (0, 0, 100, 80)
    x1, y1, x2, y2 = clamp_box(50, 50, 51, 51, 100, 100, min_size=4)
    assert (x1, y1, x2, y2) == (50, 50, 54, 54)


def test_detection_to_coco_and_yolo() -> None:
    detection = Detection(10, 20, 50, 60, 0, "skruv")
    bbox, area = detection_to_coco(detection, 100, 100)
    assert bbox == [10, 20, 40, 40]
    assert area == 1600
    cx, cy, w, h = detection_to_yolo(detection, 100, 100)
    assert cx == 0.3
    assert cy == 0.4
    assert w == 0.4
    assert h == 0.4


def test_box_iou() -> None:
    assert box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert box_iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert box_iou((0, 0, 10, 10), (5, 5, 15, 15)) == 25 / 175
