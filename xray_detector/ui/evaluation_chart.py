"""Staplar för utvärderingsdialogens jämförelse (TASK-158).

Grafen ritas med QPainter och hämtar bakgrund, text och rutnät ur widgetens
palett, precis som träningsgrafen, så den följer appens ljusa och mörka tema.
Staplarna delar y-axel, så höjden går att jämföra både inom en serie och
mellan serierna; en egen skala per serie hade gjort en modell med små tal lika
hög som en med stora.
"""

from dataclasses import dataclass, field
from math import floor, log10

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPalette, QPen
from PySide6.QtWidgets import QWidget

MARGIN_LEFT = 56
MARGIN_RIGHT = 12
MARGIN_TOP = 28
MARGIN_BOTTOM = 64
TICK_COUNT = 4
NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0)
TICK_HEIGHT = 14
TICK_WIDTH = 60
GRID_ALPHA = 60
LEGEND_HEIGHT = 18
LEGEND_LINE = 14
LEGEND_GAP = 6
MIN_FONT_SIZE = 7.0
#: Andelen av en kategoris bredd som lämnas tom mellan grupperna.
GROUP_PADDING = 0.18
BAR_GAP = 3.0
MIN_HEIGHT = 160
MAX_HEIGHT = 360


@dataclass
class BarSeries:
    """En serie staplar: namn, färg och ett värde per kategori."""

    name: str
    color: QColor
    values: list[float] = field(default_factory=list)


class BarChart(QWidget):
    """Grupperade staplar med axlar, rutnät och legend.

    Kategorierna är det jämförelsen delar upp sig på — modellerna eller
    konfidensintervallen — och varje serie blir en stapel per kategori.
    percent formaterar axeln som procent, vilket andelarna använder.
    """

    def __init__(
        self,
        title: str,
        value_axis: str,
        *,
        percent: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.value_axis = value_axis
        self.percent = percent
        self.categories: list[str] = []
        self.series: list[BarSeries] = []
        self.setMinimumHeight(MIN_HEIGHT)
        self.setMaximumHeight(MAX_HEIGHT)

    def set_data(self, categories: list[str], series: list[BarSeries]) -> None:
        """Byter ut kategorierna och serierna; tomma serier ritas inte."""
        self.categories = list(categories)
        self.series = [item for item in series if item.values]
        self.update()

    def has_data(self) -> bool:
        """Sant när det finns något att rita."""
        return bool(self.categories) and bool(self.series)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        text = palette.color(QPalette.ColorRole.WindowText)
        grid = QColor(text)
        grid.setAlpha(GRID_ALPHA)
        painter.fillRect(self.rect(), palette.color(QPalette.ColorRole.Base))
        plot = self._plot_rect()
        ticks = _ticks(self._top())
        self._draw_title(painter, text)
        self._draw_axes(painter, plot, text, grid, ticks)
        self._draw_bars(painter, plot, ticks[-1])
        self._draw_legend(painter, text)

    def _top(self) -> float:
        """Det högsta värdet någon serie har, alltså axelns tak."""
        values = [value for item in self.series for value in item.values]
        return max(values) if values else 0.0

    def _plot_rect(self) -> QRectF:
        return QRectF(
            MARGIN_LEFT,
            MARGIN_TOP,
            max(1.0, self.width() - MARGIN_LEFT - MARGIN_RIGHT),
            max(1.0, self.height() - MARGIN_TOP - MARGIN_BOTTOM),
        )

    def _draw_title(self, painter: QPainter, text: QColor) -> None:
        font = QFont(self.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(text)
        painter.drawText(
            QRectF(0, 0, self.width(), MARGIN_TOP),
            Qt.AlignmentFlag.AlignCenter,
            self.title,
        )

    def _draw_axes(
        self,
        painter: QPainter,
        plot: QRectF,
        text: QColor,
        grid: QColor,
        ticks: list[float],
    ) -> None:
        painter.setFont(self._small_font())
        painter.setPen(QPen(text, 1))
        painter.drawLine(plot.topLeft(), plot.bottomLeft())
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        top = ticks[-1]
        for value in ticks:
            y = plot.bottom() - (value / top if top else 0.0) * plot.height()
            painter.setPen(QPen(grid, 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(text)
            painter.drawText(
                QRectF(0, y - TICK_HEIGHT / 2, MARGIN_LEFT - 6, TICK_HEIGHT),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._tick_text(value),
            )
        painter.save()
        painter.translate(MARGIN_LEFT / 2 - 6, plot.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-plot.height() / 2, -TICK_HEIGHT / 2, plot.height(), TICK_HEIGHT),
            Qt.AlignmentFlag.AlignCenter,
            self.value_axis,
        )
        painter.restore()
        self._draw_categories(painter, plot, text)

    def _draw_categories(self, painter: QPainter, plot: QRectF, text: QColor) -> None:
        """Kategorierna under axeln, avkortade så de ryms i sin egen spalt."""
        if not self.categories:
            return
        metrics = QFontMetrics(painter.font())
        slot = plot.width() / len(self.categories)
        for index, name in enumerate(self.categories):
            label = metrics.elidedText(name, Qt.TextElideMode.ElideRight, int(slot) - 4)
            painter.setPen(text)
            painter.drawText(
                QRectF(plot.left() + index * slot, plot.bottom() + 4, slot, TICK_HEIGHT),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )

    def _draw_bars(self, painter: QPainter, plot: QRectF, top: float) -> None:
        if not self.categories or not self.series or top <= 0:
            return
        slot = plot.width() / len(self.categories)
        group = slot * (1 - GROUP_PADDING)
        width = group / len(self.series)
        painter.setPen(Qt.PenStyle.NoPen)
        for category, _name in enumerate(self.categories):
            left = plot.left() + category * slot + (slot - group) / 2
            for position, item in enumerate(self.series):
                if category >= len(item.values):
                    continue
                height = (item.values[category] / top) * plot.height()
                if height <= 0:
                    continue
                painter.setBrush(item.color)
                painter.drawRect(
                    QRectF(
                        left + position * width,
                        plot.bottom() - height,
                        max(1.0, width - BAR_GAP),
                        height,
                    )
                )

    def _draw_legend(self, painter: QPainter, text: QColor) -> None:
        if not self.series:
            return
        font = self._small_font()
        painter.setFont(font)
        metrics = QFontMetrics(font)
        widths = [
            metrics.horizontalAdvance(item.name) + LEGEND_LINE + LEGEND_GAP
            for item in self.series
        ]
        x = (self.width() - (sum(widths) - LEGEND_GAP)) / 2
        y = self.height() - LEGEND_HEIGHT / 2
        for item, width in zip(self.series, widths, strict=True):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(item.color)
            painter.drawRect(QRectF(x, y - LEGEND_LINE / 2, LEGEND_LINE, LEGEND_LINE / 2))
            painter.setPen(text)
            painter.drawText(
                QPointF(x + LEGEND_LINE + LEGEND_GAP, y + metrics.ascent() / 2 - 1),
                item.name,
            )
            x += width

    def _tick_text(self, value: float) -> str:
        if self.percent:
            return f"{value:.0%}"
        return f"{value:.0f}" if float(value).is_integer() else f"{value:.2f}"

    def _small_font(self) -> QFont:
        font = QFont(self.font())
        size = font.pointSizeF()
        if size > 0:
            font.setPointSizeF(max(MIN_FONT_SIZE, size - 1))
        return font


def _ticks(maximum: float) -> list[float]:
    """Runda tal från noll upp till taket, så etiketterna blir läsbara."""
    if maximum <= 0:
        return [0.0, 1.0]
    raw = maximum / TICK_COUNT
    magnitude = 10 ** floor(log10(raw))
    step = next(
        (candidate * magnitude for candidate in NICE_STEPS if candidate * magnitude >= raw),
        NICE_STEPS[-1] * magnitude,
    )
    ticks = []
    value = 0.0
    while value <= maximum + step * 1e-9:
        ticks.append(round(value, 10))
        value += step
    if ticks[-1] < maximum:
        ticks.append(round(ticks[-1] + step, 10))
    return ticks
