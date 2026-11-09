"""Deterministiska klassfärger, delade mellan detektions- och annoteringsvy.

hash(class_name) seedas slumpmässigt per Python-process, vilket gjorde att
samma klass fick olika färg vid varje appstart. Här mappas klassen till ett
index i den kända klasslistan; okända klasser får ett stabilt index via CRC32
(samma värde i varje process och på alla plattformar).
"""

import zlib

from PySide6.QtGui import QColor

CLASS_COLORS = [
    QColor(255, 80, 80),
    QColor(80, 200, 120),
    QColor(80, 140, 255),
    QColor(255, 200, 60),
    QColor(220, 100, 255),
    QColor(80, 220, 220),
    QColor(255, 140, 60),
    QColor(160, 160, 160),
]


def class_color(class_name: str, known_classes: list[str] | None = None) -> QColor:
    """Ger samma färg för samma klassnamn i varje session och vy."""
    name = str(class_name)
    known_classes = known_classes or []
    try:
        index = known_classes.index(name)
    except ValueError:
        index = zlib.crc32(name.encode("utf-8"))
    return CLASS_COLORS[index % len(CLASS_COLORS)]
