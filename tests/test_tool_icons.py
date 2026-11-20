"""Ikonerna på annoteringsvyns verktygsknappar (TASK-169).

Knapparna visar en penna för rita och en hand för panorera i stället för text.
Ikonerna ritas med QPainter, så de hämtar sin färg ur paletten och behöver
ingen bildfil.
"""

from PySide6.QtCore import QSize

from xray_detector.ui.colors import TOOL_ICON_COLOR
from xray_detector.ui.tool_icons import ICON_SIZE, draw_icon, pan_icon


def _image(icon, size: int = ICON_SIZE):
    return icon.pixmap(QSize(size, size)).toImage()


def _opaque_pixels(image) -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 0
    }


def test_both_icons_are_drawn_at_the_requested_size(qapp):
    for icon in (draw_icon(), pan_icon()):
        assert not icon.isNull()
        image = _image(icon)
        assert (image.width(), image.height()) == (ICON_SIZE, ICON_SIZE)


def test_the_icons_are_different_shapes(qapp):
    assert _opaque_pixels(_image(draw_icon())) != _opaque_pixels(_image(pan_icon()))


def test_the_icons_use_the_shared_icon_color(qapp):
    for icon in (draw_icon(), pan_icon()):
        image = _image(icon)
        colors = {
            image.pixelColor(x, y).name()
            for x in range(image.width())
            for y in range(image.height())
            if image.pixelColor(x, y).alpha() == 255
        }
        assert TOOL_ICON_COLOR in colors


def test_the_icons_leave_the_corners_transparent(qapp):
    """Ikonen täcker bara sin egen form, inte en fylld kvadrat."""
    for icon in (draw_icon(), pan_icon()):
        image = _image(icon)
        corners = (
            (0, 0),
            (ICON_SIZE - 1, 0),
            (0, ICON_SIZE - 1),
            (ICON_SIZE - 1, ICON_SIZE - 1),
        )
        for x, y in corners:
            assert image.pixelColor(x, y).alpha() == 0, (x, y)
