"""Animerad upptagenindikator som kan läggas över vilken widget som helst (TASK-40).

Indikatorn är ett eget barn till den widget den täcker, så samma komponent
används av detektions-, dataset-, tränings- och annoteringsvyn. Snurran drivs
av en timer i GUI-tråden: arbetet som indikatorn ska visa måste därför ligga
utanför GUI-tråden, annars står den still.
"""

from PySide6.QtCore import QEvent, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

DEFAULT_DELAY_MS = 150
SPIN_INTERVAL_MS = 80
SPIN_STEP_DEGREES = 30
SPINNER_SIZE = 44
SPINNER_THICKNESS = 5
ARC_SPAN_DEGREES = 100
TEXT_HEIGHT = 24
OVERLAY_COLOR = QColor(0, 0, 0, 120)
TRACK_COLOR = QColor(255, 255, 255, 70)
ARC_COLOR = QColor(77, 163, 255)
TEXT_COLOR = QColor(255, 255, 255)


class BusyIndicator(QWidget):
    """Halvtransparent överlägg med snurra och text (TASK-40).

    start() visar inget direkt: först efter delay_ms tänds överlägget, så en
    operation som hinner klart innan dess aldrig hinner blinka. stop() stänger
    av både fördröjningen och snurran, oavsett om överlägget hunnit visas.
    """

    def __init__(self, parent: QWidget, delay_ms: int = DEFAULT_DELAY_MS) -> None:
        super().__init__(parent)
        self._delay_ms = delay_ms
        self._text = ""
        self._angle = 0
        self._busy = False
        self._revealed = False
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._reveal)
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(SPIN_INTERVAL_MS)
        self._spin_timer.timeout.connect(self._advance)
        parent.installEventFilter(self)
        self.hide()

    def start(self, text: str = "") -> None:
        """Markerar arbete som pågående; överlägget tänds efter fördröjningen."""
        self._text = text
        self._angle = 0
        self._busy = True
        self._delay_timer.start(self._delay_ms)

    def stop(self) -> None:
        """Avslutar arbetet och tar bort överlägget."""
        self._delay_timer.stop()
        self._spin_timer.stop()
        self._busy = False
        self._revealed = False
        self.hide()

    def is_busy(self) -> bool:
        """True från start() till stop(), även under fördröjningen."""
        return self._busy

    def is_revealed(self) -> bool:
        """True när överlägget faktiskt syns och snurran går."""
        return self._revealed

    def text(self) -> str:
        return self._text

    def angle(self) -> int:
        """Snurrans vinkel i grader; ändras för varje animationssteg."""
        return self._angle

    def _reveal(self) -> None:
        if not self._busy:
            return
        self._revealed = True
        self._fit()
        self.show()
        self.raise_()
        self._spin_timer.start()

    def _advance(self) -> None:
        self._angle = (self._angle + SPIN_STEP_DEGREES) % 360
        self.update()

    def _fit(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())

    def eventFilter(self, obj, event) -> bool:
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._fit()
        return False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), OVERLAY_COLOR)
        center = self.rect().center()
        box = QRect(
            center.x() - SPINNER_SIZE // 2,
            center.y() - SPINNER_SIZE // 2 - TEXT_HEIGHT // 2,
            SPINNER_SIZE,
            SPINNER_SIZE,
        )
        track = QPen(TRACK_COLOR)
        track.setWidth(SPINNER_THICKNESS)
        painter.setPen(track)
        painter.drawEllipse(box)
        arc = QPen(ARC_COLOR)
        arc.setWidth(SPINNER_THICKNESS)
        arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc)
        painter.drawArc(box, -self._angle * 16, ARC_SPAN_DEGREES * 16)
        if self._text:
            font = QFont()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(TEXT_COLOR)
            painter.drawText(
                QRect(0, box.bottom() + 10, self.width(), TEXT_HEIGHT),
                Qt.AlignmentFlag.AlignHCenter,
                self._text,
            )
