from __future__ import annotations

from xray_detector.models import Detection


def box_area(x1: float, y1: float, x2: float, y2: float) -> float:
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def xyxy_to_xywh(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float, float]:
    return x1, y1, max(0.0, x2 - x1), max(0.0, y2 - y1)


def xywh_to_xyxy(x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    return x, y, x + w, y + h


def clamp_box(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    width: int,
    height: int,
    min_size: float = 1.0,
) -> tuple[float, float, float, float]:
    x1 = min(max(x1, 0.0), float(width))
    y1 = min(max(y1, 0.0), float(height))
    x2 = min(max(x2, 0.0), float(width))
    y2 = min(max(y2, 0.0), float(height))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    if x2 - x1 < min_size:
        x2 = min(float(width), x1 + min_size)
        x1 = max(0.0, x2 - min_size)
    if y2 - y1 < min_size:
        y2 = min(float(height), y1 + min_size)
        y1 = max(0.0, y2 - min_size)
    return x1, y1, x2, y2


def detection_to_coco(det: Detection, width: int, height: int) -> tuple[list[float], float]:
    x1, y1, x2, y2 = clamp_box(det.x1, det.y1, det.x2, det.y2, width, height)
    x, y, w, h = xyxy_to_xywh(x1, y1, x2, y2)
    return [x, y, w, h], w * h


def detection_to_yolo(
    det: Detection, width: int, height: int
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = clamp_box(det.x1, det.y1, det.x2, det.y2, width, height)
    cx = (x1 + x2) / 2.0 / width
    cy = (y1 + y2) / 2.0 / height
    w = (x2 - x1) / width
    h = (y2 - y1) / height
    return cx, cy, w, h


def box_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    intersection = box_area(ix1, iy1, ix2, iy2)
    if intersection <= 0:
        return 0.0
    union = box_area(ax1, ay1, ax2, ay2) + box_area(bx1, by1, bx2, by2) - intersection
    return intersection / union if union else 0.0
