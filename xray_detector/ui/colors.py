"""Deterministiska klassfärger, delade mellan detektions-, dataset- och annoteringsvyn.

Färgen ska bara bero på klassnamnet: samma klass har samma färg i varje vy, i
varje bild och vid varje appstart (TASK-76). Tidigare mappades en känd klass
till sin plats i en klasslista, så samma klass fick olika färg beroende på
vilken lista som skickades in och i vilken ordning den låg. Nu hashas namnet i
stället, vilket ger ett index som varken beror av listor eller av Pythons
hash-seed (som slumpas per process).

Paletten har 16 färger med jämnt fördelade kulörer och samma ljushet, så alla
syns mot den mörka videobilden och fungerar som bakgrund bakom mörk text i
datasetmärkena. Ett hashat index kan ge två klasser samma färg; det är priset
för att färgen inte får bero på vilka andra klasser som råkar finnas.
"""

import hashlib

from PySide6.QtGui import QColor

CLASS_COLORS = [
    QColor("#f54141"),
    QColor("#f58341"),
    QColor("#f5c841"),
    QColor("#ddf541"),
    QColor("#9bf541"),
    QColor("#59f541"),
    QColor("#41f56e"),
    QColor("#41f5b3"),
    QColor("#41f5f5"),
    QColor("#41b3f5"),
    QColor("#416ef5"),
    QColor("#5941f5"),
    QColor("#9b41f5"),
    QColor("#dd41f5"),
    QColor("#f541c8"),
    QColor("#f54183"),
]


def class_color(class_name: str) -> QColor:
    """Ger samma färg för samma klassnamn i varje session och vy."""
    digest = hashlib.md5(str(class_name).encode("utf-8")).digest()
    return CLASS_COLORS[int.from_bytes(digest[:4], "big") % len(CLASS_COLORS)]
