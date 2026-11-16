"""Klassmärket högst upp i videofönstret (TASK-84)."""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QImage, QPainter

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.detection import Detection
from xray_detector.ui.badge import (
    HIDE_FRAMES_DEFAULT,
    HIDE_FRAMES_KEY,
    SHOW_FRAMES_DEFAULT,
    SHOW_FRAMES_KEY,
    BadgeTracker,
    badge_delays,
    badge_text,
)
from xray_detector.ui.colors import class_color
from xray_detector.ui.detection_view import StreamPanel, draw_detections
from xray_detector.ui.settings_dialog import BadgeSection

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
# märket ligger 8 px från överkanten och är cirka 32 px högt; rutan i
# testramen ligger längre ner, så remsan innehåller bara märket
BADGE_STRIP = 60


def _detection(name="pistol", confidence=0.9, x1=8, y1=20, x2=40, y2=40):
    return Detection(x1, y1, x2, y2, name, confidence)


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def _panel(qapp, settings, align_right=True) -> StreamPanel:
    panel = StreamPanel("left", [], settings, badge_align_right=align_right)
    panel.display.setFixedSize(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    panel.show()
    qapp.processEvents()
    return panel


def _frame(detections) -> StreamFrame:
    return StreamFrame("left", synthetic_frame(width=64, height=48), detections, "kamera")


def _badge_pixels(pixmap, left_half: bool) -> int:
    """Antal pixlar i klassens färg i märkesremsan, i valfri halva av bilden."""
    image = pixmap.toImage()
    color = class_color("pistol").name()
    start, end = (0, image.width() // 2) if left_half else (image.width() // 2, image.width())
    return sum(
        1
        for x in range(start, end)
        for y in range(BADGE_STRIP)
        if image.pixelColor(x, y).name() == color
    )


def test_badge_waits_for_show_frames():
    tracker = BadgeTracker(show_frames=3, hide_frames=10)

    assert tracker.update([_detection()]) is None
    assert tracker.update([_detection()]) is None
    assert tracker.update([_detection()]).class_name == "pistol"


def test_show_counter_restarts_when_the_class_disappears():
    tracker = BadgeTracker(show_frames=3, hide_frames=10)
    tracker.update([_detection()])
    tracker.update([_detection()])

    tracker.update([])
    tracker.update([_detection()])

    assert tracker.update([_detection()]) is None
    assert tracker.update([_detection()]).class_name == "pistol"


def test_badge_survives_a_gap_shorter_than_hide_frames():
    tracker = BadgeTracker(show_frames=1, hide_frames=3)
    tracker.update([_detection()])

    for _ in range(2):
        assert tracker.update([]).class_name == "pistol"

    assert tracker.update([]) is None


def test_badge_hides_after_hide_frames_without_detection():
    tracker = BadgeTracker(show_frames=1, hide_frames=10)
    tracker.update([_detection()])

    for _ in range(9):
        assert tracker.update([]) is not None

    assert tracker.update([]) is None


def test_highest_confidence_class_is_shown():
    tracker = BadgeTracker(show_frames=1, hide_frames=1)

    result = tracker.update(
        [_detection("kniv", 0.6), _detection("pistol", 0.9), _detection("pistol", 0.5)]
    )

    assert result.class_name == "pistol"
    assert result.confidence == 0.9


def test_reset_clears_the_tracking():
    tracker = BadgeTracker(show_frames=1, hide_frames=10)
    tracker.update([_detection()])

    tracker.reset()

    assert tracker.update([]) is None


def test_badge_text_holds_class_and_percentage():
    assert badge_text(_detection("pistol", 0.873)) == "pistol 87 %"


def test_delays_fall_back_to_defaults_without_settings():
    assert badge_delays(None) == (SHOW_FRAMES_DEFAULT, HIDE_FRAMES_DEFAULT)


def test_panel_reads_delays_from_settings(qapp, settings):
    settings.setValue(SHOW_FRAMES_KEY, 4)
    settings.setValue(HIDE_FRAMES_KEY, 12)

    panel = StreamPanel("left", [], settings)

    assert (panel.badge.show_frames, panel.badge.hide_frames) == (4, 12)


def test_badge_sits_top_right_in_the_left_panel(qapp, settings):
    panel = _panel(qapp, settings, align_right=True)

    for _ in range(SHOW_FRAMES_DEFAULT):
        panel.show_frame(_frame([_detection()]))

    pixmap = panel.display.pixmap()
    assert _badge_pixels(pixmap, left_half=False) > 0
    assert _badge_pixels(pixmap, left_half=True) == 0


def test_badge_sits_top_left_in_the_right_panel(qapp, settings):
    panel = _panel(qapp, settings, align_right=False)

    for _ in range(SHOW_FRAMES_DEFAULT):
        panel.show_frame(_frame([_detection()]))

    pixmap = panel.display.pixmap()
    assert _badge_pixels(pixmap, left_half=True) > 0
    assert _badge_pixels(pixmap, left_half=False) == 0


def test_badge_is_not_drawn_before_show_frames(qapp, settings):
    panel = _panel(qapp, settings)

    for _ in range(SHOW_FRAMES_DEFAULT - 1):
        panel.show_frame(_frame([_detection()]))

    pixmap = panel.display.pixmap()
    assert _badge_pixels(pixmap, left_half=False) == 0


def test_clear_overlay_hides_the_badge_at_once(qapp, settings):
    panel = _panel(qapp, settings)
    for _ in range(SHOW_FRAMES_DEFAULT):
        panel.show_frame(_frame([_detection()]))
    assert _badge_pixels(panel.display.pixmap(), left_half=False) > 0

    panel.clear_overlay()

    assert _badge_pixels(panel.display.pixmap(), left_half=False) == 0


def test_label_text_is_doubled(qapp):
    """Etiketten ritas i 20 pt; den tidigare 10 pt nådde cirka 15 px över rutan."""
    image = QImage(240, 160, QImage.Format.Format_RGB888)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    draw_detections(painter, [_detection(x1=20, y1=100, x2=200, y2=150)])
    painter.end()

    color = class_color("pistol").name()
    top = min(
        y
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).name() == color
    )

    assert top <= 100 - 20


def test_badge_section_saves_and_reports_the_delays(qapp, settings):
    applied = []
    section = BadgeSection(settings, lambda: applied.append(badge_delays(settings)))

    section.show_frames.setValue(5)
    section.hide_frames.setValue(20)

    assert settings.value(SHOW_FRAMES_KEY, type=int) == 5
    assert settings.value(HIDE_FRAMES_KEY, type=int) == 20
    assert applied[-1] == (5, 20)


def test_detection_view_applies_new_delays_to_both_panels(qapp, tmp_path):
    from xray_detector.ui.detection_view import DetectionView

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(
        config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    )
    section = next(
        item for item in view._settings_sections() if isinstance(item, BadgeSection)
    )

    section.show_frames.setValue(7)
    section.hide_frames.setValue(4)

    for panel in (view.left, view.right):
        assert (panel.badge.show_frames, panel.badge.hide_frames) == (7, 4)
    view.stop()
