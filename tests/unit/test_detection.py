from __future__ import annotations

import pytest

from xray_detector.domain.detection import BBox
from xray_detector.infrastructure.detectors.base import FakeDetector
from xray_detector.infrastructure.detectors.registry import create_detector


def test_bbox_normalizes_and_clips():
    bbox = BBox(100, 80, 20, 10)
    assert (bbox.x1, bbox.y1, bbox.x2, bbox.y2) == (20, 10, 100, 80)
    assert bbox.width == 80
    assert bbox.height == 70
    assert bbox.area == 5600

    clipped = bbox.clip(50, 50)
    assert clipped == BBox(20, 10, 50, 50)
    assert bbox.to_xywh() == (20, 10, 80, 70)


def test_bbox_normalized_roundtrip():
    bbox = BBox(10, 20, 110, 220)
    values = bbox.to_normalized(200, 400)
    restored = BBox.from_normalized(*values, 200, 400)
    assert restored.x1 == pytest.approx(bbox.x1)
    assert restored.y2 == pytest.approx(bbox.y2)


def test_fake_detector_returns_expected_box(frame):
    detector = FakeDetector(
        boxes=[(10, 20, 110, 100)],
        class_name="part",
        score=0.75,
    )
    detector.load()
    detections = detector.predict(frame)
    assert len(detections) == 1
    detection = detections[0]
    assert detection.class_name == "part"
    assert detection.score == 0.75
    assert detection.bbox.to_xywh() == (10, 20, 100, 80)


def test_unknown_family_raises(frame):
    from pathlib import Path

    from xray_detector.domain.detection import ModelMetadata
    from xray_detector.infrastructure.detectors.base import DetectorError

    metadata = ModelMetadata(id="x", name="x", family="unknown", path=Path("x"))
    with pytest.raises(DetectorError):
        create_detector(metadata, None)  # type: ignore[arg-type]
