"""Klassmärket högst upp i videofönstret (TASK-84)."""

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
    SWAP_FRAMES_DEFAULT,
    SWAP_FRAMES_KEY,
    BadgeTracker,
    badge_delays,
    badge_swap_frames,
    badge_text,
)
from xray_detector.ui.colors import class_color
from xray_detector.ui.settings_dialog import BadgeSection
from xray_detector.ui.stream_panel import StreamPanel, draw_detections

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
# märket ligger 8 px från överkanten och är cirka 32 px högt; rutan i
# testramen ligger längre ner, så remsan innehåller bara märket
BADGE_STRIP = 60
# två staplade märken tar cirka 68 px; rutan börjar först vid 100 px
TWO_BADGE_STRIP = 80


def _detection(name="pistol", confidence=0.9, x1=8, y1=20, x2=40, y2=40):
    return Detection(x1, y1, x2, y2, name, confidence)




def _panel(qapp, settings, align_right=True) -> StreamPanel:
    panel = StreamPanel("left", [], settings, badge_align_right=align_right)
    panel.display.setFixedSize(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    panel.show()
    qapp.processEvents()
    return panel


def _frame(detections) -> StreamFrame:
    return StreamFrame("left", synthetic_frame(width=64, height=48), detections, "kamera")


def _badge_pixels(pixmap, left_half: bool, color="pistol", strip=BADGE_STRIP) -> int:
    """Antal pixlar i klassens färg i märkesremsan, i valfri halva av bilden."""
    image = pixmap.toImage()
    name = class_color(color).name()
    start, end = (0, image.width() // 2) if left_half else (image.width() // 2, image.width())
    return sum(
        1
        for x in range(start, end)
        for y in range(strip)
        if image.pixelColor(x, y).name() == name
    )


def _badge_rows(pixmap, color: str, left_half: bool) -> list[int]:
    """Raderna i märkesremsan som innehåller klassens färg."""
    image = pixmap.toImage()
    name = class_color(color).name()
    start, end = (0, image.width() // 2) if left_half else (image.width() // 2, image.width())
    return [
        y
        for y in range(TWO_BADGE_STRIP)
        if any(image.pixelColor(x, y).name() == name for x in range(start, end))
    ]


def test_badge_waits_for_show_frames():
    tracker = BadgeTracker(show_frames=3, hide_frames=10)

    assert tracker.update([_detection()]) == []
    assert tracker.update([_detection()]) == []
    assert tracker.update([_detection()])[0].class_name == "pistol"


def test_show_counter_restarts_when_the_class_disappears():
    tracker = BadgeTracker(show_frames=3, hide_frames=10)
    tracker.update([_detection()])
    tracker.update([_detection()])

    tracker.update([])
    tracker.update([_detection()])

    assert tracker.update([_detection()]) == []
    assert tracker.update([_detection()])[0].class_name == "pistol"


def test_badge_survives_a_gap_shorter_than_hide_frames():
    tracker = BadgeTracker(show_frames=1, hide_frames=3)
    tracker.update([_detection()])

    for _ in range(2):
        assert tracker.update([])[0].class_name == "pistol"

    assert tracker.update([]) == []


def test_badge_hides_after_hide_frames_without_detection():
    tracker = BadgeTracker(show_frames=1, hide_frames=10)
    tracker.update([_detection()])

    for _ in range(9):
        assert tracker.update([]) != []

    assert tracker.update([]) == []


def test_every_detected_class_gets_a_badge_highest_confidence_first():
    tracker = BadgeTracker(show_frames=1, hide_frames=1)

    result = tracker.update(
        [_detection("kniv", 0.6), _detection("pistol", 0.9), _detection("pistol", 0.5)]
    )

    assert [detection.class_name for detection in result] == ["pistol", "kniv"]
    assert result[0].confidence == 0.9


def test_class_still_waiting_for_show_frames_gets_no_badge():
    tracker = BadgeTracker(show_frames=2, hide_frames=10)

    assert tracker.update([_detection("pistol")]) == []
    assert [item.class_name for item in tracker.update([_detection("pistol")])] == [
        "pistol"
    ]

    result = tracker.update([_detection("pistol"), _detection("kniv")])

    assert [item.class_name for item in result] == ["pistol"]


def test_a_class_that_disappears_leaves_the_others_alone():
    tracker = BadgeTracker(show_frames=1, hide_frames=1)
    tracker.update([_detection("pistol", 0.9), _detection("kniv", 0.6)])

    result = tracker.update([_detection("kniv", 0.6)])

    assert [item.class_name for item in result] == ["kniv"]


def test_reset_clears_the_tracking():
    tracker = BadgeTracker(show_frames=1, hide_frames=10)
    tracker.update([_detection()])

    tracker.reset()

    assert tracker.update([]) == []


def _order(tracker, detections) -> list[str]:
    return [detection.class_name for detection in tracker.update(detections)]


def test_badges_keep_their_places_when_the_confidence_crosses():
    """Två klasser med nästan samma sannolikhet ska inte byta plats varje ram (TASK-86)."""
    tracker = BadgeTracker(show_frames=1, hide_frames=10, swap_frames=10)
    assert _order(tracker, [_detection("pistol", 0.90), _detection("kniv", 0.89)]) == [
        "pistol",
        "kniv",
    ]

    for frame in range(20):
        high, low = (0.91, 0.90) if frame % 2 else (0.90, 0.91)
        assert _order(
            tracker, [_detection("pistol", high), _detection("kniv", low)]
        ) == ["pistol", "kniv"]


def test_a_class_takes_the_top_place_after_swap_frames():
    tracker = BadgeTracker(show_frames=1, hide_frames=10, swap_frames=3)
    tracker.update([_detection("pistol", 0.90), _detection("kniv", 0.80)])
    steadier = [_detection("kniv", 0.95), _detection("pistol", 0.90)]

    assert _order(tracker, steadier) == ["pistol", "kniv"]
    assert _order(tracker, steadier) == ["pistol", "kniv"]
    assert _order(tracker, steadier) == ["kniv", "pistol"]


def test_swap_counter_restarts_when_the_order_goes_back():
    tracker = BadgeTracker(show_frames=1, hide_frames=10, swap_frames=3)
    tracker.update([_detection("pistol", 0.90), _detection("kniv", 0.80)])
    kniv_first = [_detection("kniv", 0.95), _detection("pistol", 0.90)]
    pistol_first = [_detection("pistol", 0.95), _detection("kniv", 0.90)]

    _order(tracker, kniv_first)
    _order(tracker, kniv_first)
    assert _order(tracker, pistol_first) == ["pistol", "kniv"]

    assert _order(tracker, kniv_first) == ["pistol", "kniv"]
    assert _order(tracker, kniv_first) == ["pistol", "kniv"]
    assert _order(tracker, kniv_first) == ["kniv", "pistol"]


def test_a_new_class_gets_its_badge_while_a_swap_is_pending():
    """En klass som tillkommer ska inte vänta på ett pågående platsbyte (TASK-86)."""
    tracker = BadgeTracker(show_frames=1, hide_frames=10, swap_frames=10)
    tracker.update([_detection("pistol", 0.90), _detection("kniv", 0.80)])

    result = _order(
        tracker,
        [_detection("kniv", 0.95), _detection("pistol", 0.90), _detection("yxa", 0.50)],
    )

    assert result == ["pistol", "kniv", "yxa"]


def test_swap_frames_fall_back_to_default_without_settings():
    assert badge_swap_frames(None) == SWAP_FRAMES_DEFAULT


def test_badge_text_holds_class_and_percentage():
    assert badge_text(_detection("pistol", 0.873)) == "pistol 87 %"


def test_delays_fall_back_to_defaults_without_settings():
    assert badge_delays(None) == (SHOW_FRAMES_DEFAULT, HIDE_FRAMES_DEFAULT)


def test_panel_reads_delays_from_settings(qapp, settings):
    settings.setValue(SHOW_FRAMES_KEY, 4)
    settings.setValue(HIDE_FRAMES_KEY, 12)

    panel = StreamPanel("left", [], settings)

    assert (panel.badge.show_frames, panel.badge.hide_frames) == (4, 12)


def test_panel_reads_swap_frames_from_settings(qapp, settings):
    settings.setValue(SWAP_FRAMES_KEY, 4)

    panel = StreamPanel("left", [], settings)

    assert panel.badge.swap_frames == 4


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


def test_both_detected_classes_get_a_badge(qapp, settings):
    panel = _panel(qapp, settings)

    for _ in range(SHOW_FRAMES_DEFAULT):
        panel.show_frame(_frame([_detection("pistol", 0.9), _detection("kniv", 0.6)]))

    pixmap = panel.display.pixmap()
    assert _badge_pixels(pixmap, left_half=False, color="pistol") > 0
    assert _badge_pixels(pixmap, left_half=False, color="kniv") > 0


def test_the_second_badge_sits_below_the_first(qapp, settings):
    panel = _panel(qapp, settings)

    for _ in range(SHOW_FRAMES_DEFAULT):
        panel.show_frame(_frame([_detection("pistol", 0.9), _detection("kniv", 0.6)]))

    pixmap = panel.display.pixmap()
    pistol = _badge_rows(pixmap, "pistol", left_half=False)
    kniv = _badge_rows(pixmap, "kniv", left_half=False)

    assert max(pistol) < min(kniv)


def test_the_badge_order_stays_put_when_the_confidence_crosses(qapp, settings):
    """Märkena ska inte byta plats varje ram när sannolikheterna korsar varandra (TASK-86)."""
    panel = _panel(qapp, settings)
    for _ in range(SHOW_FRAMES_DEFAULT):
        panel.show_frame(_frame([_detection("pistol", 0.90), _detection("kniv", 0.60)]))

    for frame in range(6):
        high, low = (0.61, 0.60) if frame % 2 else (0.60, 0.61)
        panel.show_frame(_frame([_detection("pistol", high), _detection("kniv", low)]))

    pixmap = panel.display.pixmap()
    pistol = _badge_rows(pixmap, "pistol", left_half=False)
    kniv = _badge_rows(pixmap, "kniv", left_half=False)

    assert max(pistol) < min(kniv)


def test_badges_are_stacked_in_the_right_panel_too(qapp, settings):
    panel = _panel(qapp, settings, align_right=False)

    for _ in range(SHOW_FRAMES_DEFAULT):
        panel.show_frame(_frame([_detection("pistol", 0.9), _detection("kniv", 0.6)]))

    pixmap = panel.display.pixmap()
    assert _badge_pixels(pixmap, left_half=True, color="pistol") > 0
    assert _badge_pixels(pixmap, left_half=True, color="kniv") > 0
    assert _badge_pixels(pixmap, left_half=False, color="kniv") == 0


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


def test_badge_section_saves_and_reports_the_swap_frames(qapp, settings):
    applied = []
    section = BadgeSection(
        settings, lambda: applied.append(badge_swap_frames(settings))
    )

    section.swap_frames.setValue(6)

    assert settings.value(SWAP_FRAMES_KEY, type=int) == 6
    assert applied[-1] == 6


def test_badge_section_shows_the_saved_swap_frames(qapp, settings):
    settings.setValue(SWAP_FRAMES_KEY, 15)

    section = BadgeSection(settings, lambda: None)

    assert section.swap_frames.value() == 15


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


def test_detection_view_applies_new_swap_frames_to_both_panels(qapp, tmp_path):
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

    section.swap_frames.setValue(25)

    for panel in (view.left, view.right):
        assert panel.badge.swap_frames == 25
    view.stop()
