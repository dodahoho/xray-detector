"""Tidsmässig utjämning och prediktion av detektioner (TASK-33, TASK-174)."""

from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.smoothing import (
    MAX_DT,
    DetectionSmoother,
)

DT = 1 / 30


def _detection(x1=0.0, y1=0.0, x2=100.0, y2=100.0, name="kniv", confidence=0.8):
    return Detection(x1=x1, y1=y1, x2=x2, y2=y2, class_name=name, confidence=confidence)


def test_first_detection_is_held_back_until_min_hits():
    smoother = DetectionSmoother(alpha=0.5, min_hits=2)

    assert smoother.update([_detection()], DT) == []
    result = smoother.update([_detection()], DT)

    assert len(result) == 1
    assert result[0].class_name == "kniv"


def test_constant_velocity_is_shown_at_the_next_frame():
    """Rutan ska ritas där objektet är i ramen som visas, inte två ramar efter (TASK-174)."""
    smoother = DetectionSmoother(alpha=0.5, min_hits=2)
    x = 0.0
    for _ in range(12):
        result = smoother.update([_detection(x, 0, x + 100, 100)], DT)
        x += 10

    # sista anropet gjordes på x - 10 och ritas på x
    assert abs(result[0].x1 - x) < 1.0


def test_stationary_box_stays_put():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)

    for _ in range(5):
        result = smoother.update([_detection()], DT)

    assert (result[0].x1, result[0].x2) == (0.0, 100.0)


def test_jump_is_damped():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    for _ in range(3):
        smoother.update([_detection()], DT)

    result = smoother.update([_detection(2, 0, 102, 100)], DT)

    assert 0.0 < result[0].x1 < 2.0


def test_alpha_one_returns_the_detection_for_a_still_object():
    smoother = DetectionSmoother(alpha=1.0, min_hits=1)

    for _ in range(3):
        result = smoother.update([_detection(2, 0, 102, 100)], DT)

    assert (result[0].x1, result[0].x2) == (2.0, 102.0)


def test_missing_dt_does_not_extrapolate():
    """Utan tidsintervall finns ingen tid att extrapolera över."""
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    smoother.update([_detection()], DT)

    result = smoother.update([_detection(2, 0, 102, 100)], 0.0)

    assert result[0].x1 == 1.0


def test_long_gap_does_not_extrapolate():
    """Ett långt uppehåll ger ingen meningsfull hastighet, så rutan stannar."""
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    for x in (0.0, 10.0, 20.0, 30.0):
        smoother.update([_detection(x, 0, x + 100, 100)], DT)

    result = smoother.update([_detection(40, 0, 140, 100)], MAX_DT + 0.1)

    assert result[0].x1 < 40.0


def test_track_survives_short_gap():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1, max_missed=2)
    smoother.update([_detection()], DT)

    assert smoother.update([], DT) == []
    assert len(smoother._tracks) == 1

    result = smoother.update([_detection()], DT)
    assert len(result) == 1


def test_track_is_dropped_after_max_missed():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1, max_missed=2)
    smoother.update([_detection()], DT)

    for _ in range(3):
        smoother.update([], DT)

    assert smoother._tracks == []


def test_different_classes_do_not_match():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    smoother.update([_detection(name="kniv")], DT)

    result = smoother.update([_detection(name="pistol")], DT)

    assert [d.class_name for d in result] == ["pistol"]
    assert len(smoother._tracks) == 2


def test_reset_clears_tracks():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    smoother.update([_detection()], DT)

    smoother.reset()

    assert smoother._tracks == []


def test_confidence_follows_latest_detection():
    smoother = DetectionSmoother(alpha=0.5, min_hits=1)
    smoother.update([_detection(confidence=0.9)], DT)

    result = smoother.update([_detection(confidence=0.6)], DT)

    assert result[0].confidence == 0.6
