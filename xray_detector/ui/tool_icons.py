"""Ikoner för annoteringsvyns verktygsknappar (TASK-169).

Knapparna i zoompanelen visar bara en ikon, så de tar mindre plats än texten
"Rita" och "Panorera" och panelen skymmer mindre av bilden. Ikonerna ritas med
QPainter i samma stil som temaväxlarens sol och måne, så de hämtar sin färg ur
paletten i stället för att vara bildfiler.

En vald knapp har blå bakgrund, så ikonen finns i två varianter: en grå för den
ovalda knappen och en ljus för den valda. Qt byter variant själv när knappen
markeras.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap

from xray_detector.ui.colors import TEXT_LIGHT, TOOL_ICON_COLOR

ICON_SIZE = 16
#: Pennans mått i andelar av ikonens sida, före rotationen.
PENCIL_WIDTH = 0.22
PENCIL_TOP = -0.10
PENCIL_BOTTOM = 0.42
PENCIL_TIP = -0.44
#: Pennan lutar uppåt höger, som pennikoner brukar göra.
PENCIL_ANGLE = 45
#: Handflatans mått och de fyra fingrarnas vänsterkant och överkant.
PALM = (0.26, 0.40, 0.48, 0.44)
FINGERS = ((0.28, 0.20), (0.40, 0.10), (0.52, 0.14), (0.64, 0.22))
FINGER_WIDTH = 0.10
FINGER_BOTTOM = 0.52
#: Tummen sitter till vänster om handflatan och lutar utåt.
THUMB_ORIGIN = (0.26, 0.54)
THUMB_ANGLE = -40
THUMB = (-0.05, -0.18, 0.10, 0.24)


def _scaled(rect: tuple[float, float, float, float], size: int) -> QRectF:
    return QRectF(*(value * size for value in rect))


def _pencil(painter: QPainter, size: int) -> None:
    painter.translate(size / 2, size / 2)
    painter.rotate(PENCIL_ANGLE)
    half = size * PENCIL_WIDTH / 2
    pencil = QPainterPath()
    pencil.moveTo(-half, size * PENCIL_TOP)
    pencil.lineTo(0, size * PENCIL_TIP)
    pencil.lineTo(half, size * PENCIL_TOP)
    pencil.lineTo(half, size * PENCIL_BOTTOM)
    pencil.lineTo(-half, size * PENCIL_BOTTOM)
    pencil.closeSubpath()
    painter.drawPath(pencil)


def _hand(painter: QPainter, size: int) -> None:
    painter.drawRoundedRect(_scaled(PALM, size), 0.10 * size, 0.10 * size)
    for left, top in FINGERS:
        painter.drawRoundedRect(
            QRectF(
                left * size,
                top * size,
                FINGER_WIDTH * size,
                (FINGER_BOTTOM - top) * size,
            ),
            0.05 * size,
            0.05 * size,
        )
    painter.save()
    painter.translate(THUMB_ORIGIN[0] * size, THUMB_ORIGIN[1] * size)
    painter.rotate(THUMB_ANGLE)
    painter.drawRoundedRect(_scaled(THUMB, size), 0.05 * size, 0.05 * size)
    painter.restore()


def _pixmap(shape, size: int, color: str) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    shape(painter, size)
    painter.end()
    return pixmap


def _icon(shape, size: int) -> QIcon:
    """Ikonen i grått för den ovalda knappen och ljust för den valda."""
    icon = QIcon()
    icon.addPixmap(_pixmap(shape, size, TOOL_ICON_COLOR), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_pixmap(shape, size, TEXT_LIGHT), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def draw_icon(size: int = ICON_SIZE) -> QIcon:
    """Penna: ett klick väljer rita-verktyget."""
    return _icon(_pencil, size)


def pan_icon(size: int = ICON_SIZE) -> QIcon:
    """Öppen hand: ett klick väljer panorera-verktyget."""
    return _icon(_hand, size)
