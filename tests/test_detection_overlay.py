"""Detektionsoverlayn ritar klassens färg (TASK-76)."""

from PySide6.QtCore import QSettings

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.detection import Detection
from xray_detector.ui.colors import class_color
from xray_detector.ui.detection_view import StreamPanel


def _colors(pixmap) -> set[str]:
    image = pixmap.toImage()
    return {
        image.pixelColor(x, y).name()
        for x in range(image.width())
        for y in range(image.height())
    }


def test_overlay_draws_the_shared_class_color(qapp, tmp_path):
    """Samma klass har samma färg som i dataset- och annoteringsvyn."""
    panel = StreamPanel(
        "left", [], QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    )
    panel.resize(320, 240)
    panel.show()
    qapp.processEvents()

    panel.show_frame(
        StreamFrame(
            "left",
            synthetic_frame(width=64, height=48),
            [Detection(8, 8, 40, 30, "pistol", 0.9)],
            "kamera",
        )
    )
    qapp.processEvents()

    assert class_color("pistol").name() in _colors(panel.display.pixmap())
