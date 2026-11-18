"""Knapp som växlar mellan ljust och mörkt tema (TASK-156).

Knappen ligger till höger om vyernas inställningsknapp. Ikonen visar vad ett
klick gör: en sol i mörkt läge och en måne i ljust läge. Alla knappar lyssnar på
samma signal, så en växling slår igenom i alla vyer på en gång.
"""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton

from xray_detector.ui.colors import GEAR_COLOR
from xray_detector.ui.style import ICON_BUTTON_WIDTH, apply_metrics
from xray_detector.ui.theme import is_dark, theme_changed, toggle_theme

ICON_SIZE = 16
SUN_RAYS = 8
SUN_CORE = 0.22
SUN_RAY_INNER = 0.30
SUN_RAY_OUTER = 0.46
SUN_RAY_WIDTH = 0.06
MOON_OUTER = (0.12, 0.12, 0.76, 0.76)
MOON_CUT = (0.30, 0.02, 0.76, 0.76)


class ThemeToggle(QPushButton):
    """Växlar mellan ljust och mörkt tema; ikonen visar nästa läge."""

    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        apply_metrics(self, width=ICON_BUTTON_WIDTH)
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.setAccessibleName("Byt tema")
        self.clicked.connect(self._on_clicked)
        theme_changed.changed.connect(self.refresh)
        self.refresh()

    def _on_clicked(self) -> None:
        toggle_theme(QApplication.instance(), self.settings)

    def refresh(self) -> None:
        """Ikon och verktygstips följer det aktuella temat."""
        dark = is_dark()
        self.setIcon(sun_icon() if dark else moon_icon())
        self.setToolTip("Byt till ljust tema" if dark else "Byt till mörkt tema")


def _pixmap_and_painter(size: int) -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(GEAR_COLOR))
    return pixmap, painter


def _scaled(rect: tuple[float, float, float, float], size: int) -> QRectF:
    return QRectF(*(value * size for value in rect))


def sun_icon(size: int = ICON_SIZE) -> QIcon:
    """Grå sol: ett klick går till ljust tema."""
    pixmap, painter = _pixmap_and_painter(size)
    center = size / 2
    painter.drawEllipse(QPointF(center, center), size * SUN_CORE, size * SUN_CORE)
    for index in range(SUN_RAYS):
        painter.save()
        painter.translate(center, center)
        painter.rotate(index * 360 / SUN_RAYS)
        painter.drawRoundedRect(
            QRectF(
                -size * SUN_RAY_WIDTH / 2,
                -size * SUN_RAY_OUTER,
                size * SUN_RAY_WIDTH,
                size * (SUN_RAY_OUTER - SUN_RAY_INNER),
            ),
            size * SUN_RAY_WIDTH / 2,
            size * SUN_RAY_WIDTH / 2,
        )
        painter.restore()
    painter.end()
    return QIcon(pixmap)


def moon_icon(size: int = ICON_SIZE) -> QIcon:
    """Grå måne: ett klick går till mörkt tema."""
    pixmap, painter = _pixmap_and_painter(size)
    outer = QPainterPath()
    outer.addEllipse(_scaled(MOON_OUTER, size))
    cut = QPainterPath()
    cut.addEllipse(_scaled(MOON_CUT, size))
    painter.drawPath(outer.subtracted(cut))
    painter.end()
    return QIcon(pixmap)
