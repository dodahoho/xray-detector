"""Graf över loss och mAP per epok i träningsvyn (TASK-45).

Loss och mAP har olika skalor, så de ritas i var sin graf med egen axel i
stället för på en gemensam y-axel. QtCharts följer med PySide6 och kräver
ingen ny dependency.
"""

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
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


class TrainingChart(QWidget):
    """Två grafer som fylls på med ett epokevent i taget.

    Serierna är publika så testerna kan läsa punkterna utan att rita av
    widgeten. En körning med en enda epok ger en punkt; axlarna spänner då
    över ett minsta intervall och punkten ritas som en markör, annars hade
    grafen sett tom ut.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.train_loss = _series("Train-loss")
        self.val_loss = _series("Val-loss")
        self.map50 = _series("mAP50")
        self.map50_95 = _series("mAP50-95")

        self.loss_chart, self.loss_axis_x, self.loss_axis_y = _chart(
            LOSS_TITLE, LOSS_AXIS, [self.train_loss, self.val_loss]
        )
        self.map_chart, self.map_axis_x, self.map_axis_y = _chart(
            MAP_TITLE, MAP_AXIS, [self.map50, self.map50_95]
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_view(self.loss_chart))
        layout.addWidget(_view(self.map_chart))
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
        _fit(self.loss_chart, self.loss_axis_x, self.loss_axis_y,
             [self.train_loss, self.val_loss], MIN_LOSS_SPAN)
        _fit(self.map_chart, self.map_axis_x, self.map_axis_y,
             [self.map50, self.map50_95], MIN_MAP_SPAN)


def _series(name: str) -> QLineSeries:
    series = QLineSeries()
    series.setName(name)
    series.setPointsVisible(True)
    series.setMarkerSize(MARKER_SIZE)
    return series


def _chart(title: str, value_axis: str, series: list[QLineSeries]):
    chart = QChart()
    chart.setTitle(title)
    chart.legend().setVisible(True)
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
    for item in series:
        chart.addSeries(item)
    axis_x = QValueAxis()
    axis_x.setTitleText(EPOCH_AXIS)
    axis_x.setLabelFormat("%d")
    axis_y = QValueAxis()
    axis_y.setTitleText(value_axis)
    axis_y.setLabelFormat("%.2f")
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    for item in series:
        item.attachAxis(axis_x)
        item.attachAxis(axis_y)
    return chart, axis_x, axis_y


def _view(chart: QChart) -> QChartView:
    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setMinimumHeight(160)
    # grafen behöver inte mer höjd än så; loggen under får resten av vyn
    view.setMaximumHeight(360)
    return view


def _fit(chart: QChart, axis_x: QValueAxis, axis_y: QValueAxis,
         series: list[QLineSeries], min_span: float) -> None:
    """Sätter axelintervallen så alla punkter syns, även en enda."""
    points = [point for item in series for point in item.points()]
    if not points:
        axis_x.setRange(0, 1)
        axis_y.setRange(0, 1)
        return
    epochs = [point.x() for point in points]
    values = [point.y() for point in points]
    axis_x.setRange(*_span(epochs, 1.0))
    axis_y.setRange(*_span(values, min_span))


def _span(values: list[float], min_span: float) -> tuple[float, float]:
    low, high = min(values), max(values)
    if high - low < min_span:
        middle = (low + high) / 2
        return middle - min_span / 2, middle + min_span / 2
    padding = (high - low) * AXIS_PADDING
    return low - padding, high + padding
