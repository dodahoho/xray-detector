"""Graf över loss och mAP per epok i träningsvyn (TASK-45, TASK-155).

Loss och mAP har olika skalor, så de ritas i var sin graf med egen axel i
stället för på en gemensam y-axel. Grafen ritas med QPainter och hämtar
bakgrund, text och rutnät ur widgetens palett, så den följer appens ljusa och
mörka tema. QtCharts är utfasat i Qt 6.8 och borttaget i 6.10 och används
därför inte längre.
"""

from dataclasses import dataclass, field
from math import ceil, floor, log10

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QWidget

from xray_detector.domain.training import EpochMetrics

LOSS_TITLE = "Loss per epok"
MAP_TITLE = "mAP per epok"
EPOCH_AXIS = "Epok"
LOSS_AXIS = "Loss"
MAP_AXIS = "mAP"
MIN_LOSS_SPAN = 0.1
MIN_MAP_SPAN = 0.1
MARKER_SIZE = 6.0
AXIS_PADDING = 0.1

#: Seriefärgerna ligger fast och är valda för att synas mot både ljus och mörk
#: bakgrund. Axlar, rutnät och text hämtas i stället ur paletten.
TRAIN_LOSS_COLOR = QColor("#4da3ff")
VAL_LOSS_COLOR = QColor("#e08a2e")
MAP50_COLOR = QColor("#3fae6a")
MAP50_95_COLOR = QColor("#d9534f")

MARGIN_LEFT = 56
MARGIN_RIGHT = 12
MARGIN_TOP = 28
MARGIN_BOTTOM = 56
TICK_COUNT = 4
NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0)
TICK_HEIGHT = 14
TICK_WIDTH = 60
GRID_ALPHA = 60
LEGEND_HEIGHT = 18
LEGEND_LINE = 14
LEGEND_GAP = 6
MIN_FONT_SIZE = 7.0


@dataclass
class Series:
    """En serie i grafen: namn, färg och punkter som (epok, värde)."""

    name: str
    color: QColor
    points: list[tuple[float, float]] = field(default_factory=list)

    def append(self, x: float, y: float) -> None:
        self.points.append((x, y))

    def clear(self) -> None:
        self.points.clear()

    def count(self) -> int:
        return len(self.points)


@dataclass
class Axis:
    """Axelns titel och intervall; intervallet räknas fram ur punkterna."""

    title: str
    minimum: float = 0.0
    maximum: float = 1.0

    def set_range(self, minimum: float, maximum: float) -> None:
        self.minimum = minimum
        self.maximum = maximum

    def fraction(self, value: float) -> float:
        """Värdets läge mellan axelns ändar: 0 vid minimum, 1 vid maximum."""
        span = self.maximum - self.minimum
        return 0.0 if span <= 0 else (value - self.minimum) / span


class LineChart(QWidget):
    """En graf med axlar, rutnät, polylinjer, markörer och legend."""

    def __init__(
        self,
        title: str,
        value_axis: str,
        series: list[Series],
        min_span: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.title = title
        self.series = series
        self.axis_x = Axis(EPOCH_AXIS)
        self.axis_y = Axis(value_axis)
        self._min_span = min_span
        self.setMinimumHeight(160)
        # grafen behöver inte mer höjd än så; loggen under får resten av vyn
        self.setMaximumHeight(360)

    def fit(self) -> None:
        """Sätter axelintervallen så alla punkter syns, även en enda."""
        points = [point for item in self.series for point in item.points]
        if not points:
            self.axis_x.set_range(0, 1)
            self.axis_y.set_range(0, 1)
        else:
            self.axis_x.set_range(*_span([point[0] for point in points], 1.0))
            self.axis_y.set_range(*_span([point[1] for point in points], self._min_span))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        text = palette.color(QPalette.ColorRole.WindowText)
        grid = QColor(text)
        grid.setAlpha(GRID_ALPHA)
        painter.fillRect(self.rect(), palette.color(QPalette.ColorRole.Base))
        plot = self._plot_rect()
        self._draw_title(painter, text)
        self._draw_axes(painter, plot, text, grid)
        self._draw_series(painter, plot)
        self._draw_legend(painter, text)

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

    def _draw_axes(self, painter: QPainter, plot: QRectF, text: QColor, grid: QColor) -> None:
        painter.setFont(self._small_font())
        painter.setPen(QPen(text, 1))
        painter.drawLine(plot.topLeft(), plot.bottomLeft())
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        for value in _ticks(self.axis_y):
            y = plot.bottom() - self.axis_y.fraction(value) * plot.height()
            painter.setPen(QPen(grid, 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(text)
            painter.drawText(
                QRectF(0, y - TICK_HEIGHT / 2, MARGIN_LEFT - 6, TICK_HEIGHT),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.2f}",
            )
        ticks_x = _ticks(self.axis_x)
        decimals = 0 if all(float(value).is_integer() for value in ticks_x) else 1
        for value in ticks_x:
            x = plot.left() + self.axis_x.fraction(value) * plot.width()
            painter.drawText(
                QRectF(x - TICK_WIDTH / 2, plot.bottom() + 4, TICK_WIDTH, TICK_HEIGHT),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                f"{value:.{decimals}f}",
            )
        painter.drawText(
            QRectF(plot.left(), plot.bottom() + 4 + TICK_HEIGHT, plot.width(), TICK_HEIGHT),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self.axis_x.title,
        )
        painter.save()
        painter.translate(MARGIN_LEFT / 2 - 6, plot.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-plot.height() / 2, -TICK_HEIGHT / 2, plot.height(), TICK_HEIGHT),
            Qt.AlignmentFlag.AlignCenter,
            self.axis_y.title,
        )
        painter.restore()

    def _draw_series(self, painter: QPainter, plot: QRectF) -> None:
        for item in self.series:
            if not item.points:
                continue
            points = [self._to_plot(point, plot) for point in item.points]
            if len(points) > 1:
                painter.setPen(QPen(item.color, 2))
                painter.drawPolyline(QPolygonF(points))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(item.color)
            for point in points:
                painter.drawEllipse(point, MARKER_SIZE / 2, MARKER_SIZE / 2)

    def _draw_legend(self, painter: QPainter, text: QColor) -> None:
        font = self._small_font()
        painter.setFont(font)
        metrics = QFontMetrics(font)
        widths = [metrics.horizontalAdvance(item.name) + LEGEND_LINE + LEGEND_GAP
                  for item in self.series]
        x = (self.width() - (sum(widths) - LEGEND_GAP)) / 2
        y = self.height() - LEGEND_HEIGHT / 2
        for item, width in zip(self.series, widths, strict=True):
            painter.setPen(QPen(item.color, 2))
            painter.drawLine(QPointF(x, y), QPointF(x + LEGEND_LINE, y))
            painter.setPen(text)
            painter.drawText(
                QPointF(x + LEGEND_LINE + LEGEND_GAP, y + metrics.ascent() / 2 - 1),
                item.name,
            )
            x += width

    def _to_plot(self, point: tuple[float, float], plot: QRectF) -> QPointF:
        return QPointF(
            plot.left() + self.axis_x.fraction(point[0]) * plot.width(),
            plot.bottom() - self.axis_y.fraction(point[1]) * plot.height(),
        )

    def _small_font(self) -> QFont:
        font = QFont(self.font())
        size = font.pointSizeF()
        if size > 0:
            font.setPointSizeF(max(MIN_FONT_SIZE, size - 1))
        return font


class TrainingChart(QWidget):
    """Två grafer som fylls på med ett epokevent i taget.

    Serierna är publika så testerna kan läsa punkterna utan att rita av
    widgeten. En körning med en enda epok ger en punkt; axlarna spänner då
    över ett minsta intervall och punkten ritas som en markör, annars hade
    grafen sett tom ut.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.train_loss = Series("Train-loss", TRAIN_LOSS_COLOR)
        self.val_loss = Series("Val-loss", VAL_LOSS_COLOR)
        self.map50 = Series("mAP50", MAP50_COLOR)
        self.map50_95 = Series("mAP50-95", MAP50_95_COLOR)

        self.loss_chart = LineChart(
            LOSS_TITLE, LOSS_AXIS, [self.train_loss, self.val_loss], MIN_LOSS_SPAN
        )
        self.map_chart = LineChart(
            MAP_TITLE, MAP_AXIS, [self.map50, self.map50_95], MIN_MAP_SPAN
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.loss_chart)
        layout.addWidget(self.map_chart)
        self._fit_axes()

    def add_epoch(self, metrics: EpochMetrics) -> None:
        """Lägger till epokens punkter; värden som saknas hoppas över."""
        for series, value in (
            (self.train_loss, metrics.train_loss),
            (self.val_loss, metrics.val_loss),
            (self.map50, metrics.map50),
            (self.map50_95, metrics.map50_95),
        ):
            if value is not None:
                series.append(metrics.epoch, value)
        self._fit_axes()

    def clear(self) -> None:
        for series in (self.train_loss, self.val_loss, self.map50, self.map50_95):
            series.clear()
        self._fit_axes()

    def has_data(self) -> bool:
        """Sant när någon serie har punkter, alltså när grafen har något att visa."""
        return any(
            series.count()
            for series in (self.train_loss, self.val_loss, self.map50, self.map50_95)
        )

    def _fit_axes(self) -> None:
        self.loss_chart.fit()
        self.map_chart.fit()


def _ticks(axis: Axis) -> list[float]:
    """Runda tal inom axelns intervall, så etiketterna blir läsbara."""
    span = axis.maximum - axis.minimum
    if span <= 0:
        return [axis.minimum]
    raw = span / TICK_COUNT
    magnitude = 10 ** floor(log10(raw))
    step = next(
        (candidate * magnitude for candidate in NICE_STEPS if candidate * magnitude >= raw),
        NICE_STEPS[-1] * magnitude,
    )
    value = ceil(axis.minimum / step) * step
    ticks = []
    while value <= axis.maximum + step * 1e-9:
        ticks.append(round(value, 10))
        value += step
    return ticks or [axis.minimum, axis.maximum]


def _span(values: list[float], min_span: float) -> tuple[float, float]:
    low, high = min(values), max(values)
    if high - low < min_span:
        middle = (low + high) / 2
        return middle - min_span / 2, middle + min_span / 2
    padding = (high - low) * AXIS_PADDING
    return low - padding, high + padding
