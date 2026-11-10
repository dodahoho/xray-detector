"""Tidsmässig utjämning av detektioner (TASK-33)."""

from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.smoothing import DetectionSmoother


def _detection(x1=0.0, y1=0.0, x2=10.0, y2=10.0, name="kniv", confidence=0.8):
    return Detection(x1=x1, y1=y1, x2=x2, y2=y2, class_name=name, confidence=confidence)


def test_first_detection_is_held_back_until_min_hits():
    smoother = DetectionSmoother(alpha=0.5, min_hits=2)

    assert smoother.update([_detection()]) == []
    result = smoother.update([_detection()])

    assert len(result) == 1
    assert result[0].class_name == "kniv"


def test_ema_damps_a_jump():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)

    smoother.update([_detection(0, 0, 10, 10)])
    result = smoother.update([_detection(2, 0, 12, 10)])

    assert (result[0].x1, result[0].x2) == (1.0, 11.0)


def test_alpha_one_returns_raw_boxes():
    smoother = DetectionSmoother(alpha=1.0, min_hits=1)

    smoother.update([_detection(0, 0, 10, 10)])
    result = smoother.update([_detection(2, 0, 12, 10)])

    assert (result[0].x1, result[0].x2) == (2.0, 12.0)


def test_track_survives_short_gap():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1, max_missed=2)
    smoother.update([_detection()])

    assert smoother.update([]) == []
    assert len(smoother._tracks) == 1

    result = smoother.update([_detection()])
    assert len(result) == 1


def test_track_is_dropped_after_max_missed():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1, max_missed=2)
    smoother.update([_detection()])

    for _ in range(3):
        smoother.update([])

    assert smoother._tracks == []


def test_different_classes_do_not_match():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    smoother.update([_detection(name="kniv")])

    result = smoother.update([_detection(name="pistol")])

    assert [d.class_name for d in result] == ["pistol"]
    assert len(smoother._tracks) == 2


def test_reset_clears_tracks():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    smoother.update([_detection()])

    smoother.reset()

    assert smoother._tracks == []


def test_confidence_follows_latest_detection():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    smoother.update([_detection(confidence=0.9)])

    result = smoother.update([_detection(confidence=0.6)])

    assert result[0].confidence == 0.6
