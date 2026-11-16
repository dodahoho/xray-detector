"""Klassmärket högst upp i videofönstret (TASK-84).

Rutans etikett sitter på objektet och kan drunkna i bilden: texten är liten
och klassfärgen kan ha dålig kontrast mot det som ligger bakom. Märket visar
samma klass och sannolikhet på en fast plats i fönstret, med klassens färg som
bakgrund.

En detektion nära confidence-tröskeln slår av och på mellan ramar, så märket
kräver ett antal ramar i följd med klassen innan det visas och lika många utan
innan det döljs. Fördröjningarna är inställbara och räknas i ramar, eftersom
det är ramar som flimrar.

Detekteras flera klasser samtidigt får varje klass ett eget märke, staplade
uppifrån och ned med den säkraste klassen överst. Ligger två klasser nära
varandra i sannolikhet byter de annars plats nästan varje ram, så en klass tar
bara över platsen när den varit säkrast ett antal ramar i följd (TASK-86).
"""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from xray_detector.domain.detection import Detection
from xray_detector.ui.colors import class_color

SHOW_FRAMES_KEY = "detection/badge_show_frames"
HIDE_FRAMES_KEY = "detection/badge_hide_frames"
SWAP_FRAMES_KEY = "detection/badge_swap_frames"
SHOW_FRAMES_DEFAULT = 3
HIDE_FRAMES_DEFAULT = 10
SWAP_FRAMES_DEFAULT = 10
BADGE_MARGIN = 8
BADGE_PADDING = 6
BADGE_RADIUS = 6
BADGE_GAP = 4
BADGE_POINT_SIZE = 12
DARK_TEXT = "#111"
LIGHT_TEXT = "#fff"


def badge_delays(settings) -> tuple[int, int]:
    """Antal ramar innan märket visas respektive döljs.

    Utan sparade värden används 3 ramar för att visa och 10 för att dölja,
    alltså ungefär en tiondels sekund i 30 fps.
    """
    if settings is None:
        return SHOW_FRAMES_DEFAULT, HIDE_FRAMES_DEFAULT
    return (
        _frames(settings, SHOW_FRAMES_KEY, SHOW_FRAMES_DEFAULT),
        _frames(settings, HIDE_FRAMES_KEY, HIDE_FRAMES_DEFAULT),
    )


def badge_swap_frames(settings) -> int:
    """Antal ramar i följd innan märkena byter plats (TASK-86).

    Utan sparat värde krävs 10 ramar, alltså ungefär en tredjedels sekund i
    30 fps, så två klasser med nästan samma sannolikhet inte byter plats
    varje ram.
    """
    if settings is None:
        return SWAP_FRAMES_DEFAULT
    return _frames(settings, SWAP_FRAMES_KEY, SWAP_FRAMES_DEFAULT)


def _frames(settings, key: str, default: int) -> int:
    try:
        return max(1, int(settings.value(key, default, type=int)))
    except (TypeError, ValueError):
        return default


class BadgeTracker:
    """Vilka klassmärken som ska visas, med hysteres över ramar.

    Varje klass räknar sammanhängande ramar med och utan detektion. Klassen
    syns när den setts show_frames ramar i följd och släcks först efter
    hide_frames ramar utan, så enstaka missade ramar inte får märket att
    flimra. Flera klasser kan synas samtidigt och får då varsitt märke.

    Märkena ligger i en egen ordning som också har hysteres: den säkraste
    klassen ligger överst, men en klass tar bara över platsen när den varit
    säkrast swap_frames ramar i följd (TASK-86). Två klasser med nästan samma
    sannolikhet byter då inte plats varje ram.
    """

    def __init__(
        self,
        show_frames: int = SHOW_FRAMES_DEFAULT,
        hide_frames: int = HIDE_FRAMES_DEFAULT,
        swap_frames: int = SWAP_FRAMES_DEFAULT,
    ) -> None:
        self._hits: dict[str, int] = {}
        self._misses: dict[str, int] = {}
        self._last: dict[str, Detection] = {}
        self._visible: set[str] = set()
        self._order: list[str] = []
        self._pending: list[str] | None = None
        self._pending_frames = 0
        self.set_delays(show_frames, hide_frames)
        self.set_swap_frames(swap_frames)

    def set_delays(self, show_frames: int, hide_frames: int) -> None:
        """Nya fördröjningar slår igenom direkt, utan att nollställa läget."""
        self.show_frames = max(1, int(show_frames))
        self.hide_frames = max(1, int(hide_frames))

    def set_swap_frames(self, swap_frames: int) -> None:
        """Ny tröghet i platsbyten, utan att nollställa läget (TASK-86)."""
        self.swap_frames = max(1, int(swap_frames))

    def reset(self) -> None:
        self._hits.clear()
        self._misses.clear()
        self._last.clear()
        self._visible.clear()
        self._order.clear()
        self._pending = None
        self._pending_frames = 0

    def update(self, detections: list[Detection]) -> list[Detection]:
        """Räknar ramen och returnerar märkena som ska visas, säkrast först."""
        present = _best_per_class(detections)
        for name in list(self._hits):
            if name in present:
                self._hits[name] += 1
                self._misses[name] = 0
            else:
                self._hits[name] = 0
                self._misses[name] += 1
        for name in present:
            if name not in self._hits:
                self._hits[name] = 1
                self._misses[name] = 0
        self._last.update(present)
        for name in list(self._hits):
            if name in self._visible:
                if self._misses[name] >= self.hide_frames:
                    self._visible.discard(name)
            elif self._hits[name] >= self.show_frames:
                self._visible.add(name)
        self._forget_hidden()
        self._reorder()
        return [self._last[name] for name in self._order]

    def _reorder(self) -> None:
        """Visningsordningen, med tröghet i platsbyten (TASK-86).

        Den säkraste klassen ska ligga överst, men en ny ordning gäller först
        när den efterfrågats swap_frames ramar i följd. Räknaren nollställs när
        ordningen går tillbaka, så en korsande sannolikhet inte ger något byte.
        Klasser som tillkommer sätts in direkt på sin plats, så deras märke
        inte väntar på ett pågående platsbyte.
        """
        desired = sorted(self._visible, key=self._rank)
        current = [name for name in self._order if name in self._visible]
        common = [name for name in desired if name in current]
        if common == current:
            self._order = desired
            self._pending = None
            self._pending_frames = 0
            return
        if common == self._pending:
            self._pending_frames += 1
        else:
            self._pending = common
            self._pending_frames = 1
        if self._pending_frames >= self.swap_frames:
            self._order = desired
            self._pending = None
            self._pending_frames = 0
            return
        self._order = _with_new_classes(current, desired)

    def _rank(self, name: str) -> tuple[float, str]:
        """Sorteringsnyckel: säkrast först, sedan klassnamn så ordningen är stabil."""
        return -self._last[name].confidence, name

    def _forget_hidden(self) -> None:
        """Glömmer klasser som varken syns eller är på väg tillbaka."""
        for name in list(self._hits):
            if name in self._visible or self._hits[name]:
                continue
            if self._misses[name] < self.hide_frames:
                continue
            del self._hits[name]
            del self._misses[name]
            self._last.pop(name, None)


def _best_per_class(detections: list[Detection]) -> dict[str, Detection]:
    """Klassens säkraste detektion i ramen; flera rutor av samma klass räknas en gång."""
    best: dict[str, Detection] = {}
    for detection in detections:
        current = best.get(detection.class_name)
        if current is None or detection.confidence > current.confidence:
            best[detection.class_name] = detection
    return best


def _with_new_classes(order: list[str], desired: list[str]) -> list[str]:
    """Lägger till nya klasser på sin plats utan att röra de befintligas ordning.

    Ordningen behålls när ett platsbyte väntar, men en klass som just blivit
    synlig ska ändå få sitt märke direkt. Den sätts in där den hör hemma
    bland de klasser som redan har en plats.
    """
    result = list(order)
    for index, name in enumerate(desired):
        if name in result:
            continue
        position = sum(1 for other in desired[:index] if other in result)
        result.insert(position, name)
    return result


def badge_text(detection: Detection) -> str:
    """Klass och sannolikhet som märket visar."""
    return f"{detection.class_name} {detection.confidence * 100:.0f} %"


def draw_badges(
    painter: QPainter, area: QRect, detections: list[Detection], *, align_right: bool
) -> None:
    """Ritar klass och sannolikhet högst upp i videofönstret, ett märke per klass.

    Märkena staplas uppifrån och ned med den säkraste klassen överst, så flera
    detekterade klasser syns samtidigt utan att skriva över varandra. De ritas
    på den skalade bilden, så texten har samma storlek oavsett källans
    upplösning. Bakgrunden är klassens färg, så kontrasten mot bilden bakom
    spelar ingen roll. Fler märken än det finns plats för ritas inte.
    """
    font = QFont()
    font.setPointSize(BADGE_POINT_SIZE)
    font.setBold(True)
    painter.setFont(font)
    metrics = painter.fontMetrics()
    height = metrics.height() + 2 * BADGE_PADDING
    top = area.top() + BADGE_MARGIN
    for detection in detections:
        if top + height > area.bottom() - BADGE_MARGIN:
            break
        color = class_color(detection.class_name)
        text = badge_text(detection)
        width = metrics.horizontalAdvance(text) + 2 * BADGE_PADDING
        x = (
            area.right() - BADGE_MARGIN - width
            if align_right
            else area.left() + BADGE_MARGIN
        )
        rect = QRect(x, top, width, height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, BADGE_RADIUS, BADGE_RADIUS)
        painter.setPen(QColor(DARK_TEXT if color.lightness() > 140 else LIGHT_TEXT))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        top += height + BADGE_GAP
