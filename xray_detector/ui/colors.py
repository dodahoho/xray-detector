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

#: Färger för text, ramar och ytor i vyerna. De låg tidigare som literaler i
#: varje vy, så samma grå nyans kunde betyda olika saker på olika ställen
#: (TASK-139). Nya ytor ska hämta sin färg härifrån.
TEXT_DARK = "#111"
TEXT_LIGHT = "#fff"
MUTED_TEXT = "#888"
SUBTLE_TEXT = "#aaa"
BORDER = "#444"
IDLE_BORDER = "#555"
CARD_BORDER = "#666"
GEAR_COLOR = "#8a8a8a"
SELECTED_BORDER = "#4da3ff"
SELECTED_BACKGROUND = "#1d3b57"
IDLE_BACKGROUND = "#2b2b2b"
HEADER_BACKGROUND = "#10202e"
PENDING_COLOR = "#e5a52a"
ERROR_COLOR = "#c33"
#: Zoompanelens halvtransparenta bakgrund ovanpå annoteringsbilden (TASK-163).
ZOOM_PANEL_BACKGROUND = "rgba(20, 20, 20, 170)"
#: Enhetsraden i detektionsvyn: grönt när CUDA används, rött annars.
DEVICE_CUDA_COLOR = "#2a8"
DEVICE_CPU_COLOR = "#c33"
#: Serierna i träningsgrafen. De ligger fast och är valda för att synas mot
#: både ljus och mörk bakgrund; axlar och text hämtas ur paletten (TASK-155).
TRAIN_LOSS_COLOR = "#4da3ff"
VAL_LOSS_COLOR = "#e08a2e"
MAP50_COLOR = "#3fae6a"
MAP50_95_COLOR = "#d9534f"
#: Serierna i utvärderingsdialogens staplar (TASK-158). Samma fyra som
#: träningsgrafen plus två till, valda för att synas mot både ljus och mörk
#: bakgrund och för att gå att skilja åt även när färgerna skrivs ut i grått.
SERIES_COLORS = (
    TRAIN_LOSS_COLOR,
    VAL_LOSS_COLOR,
    MAP50_COLOR,
    MAP50_95_COLOR,
    "#8e6bd6",
    "#3aa6a6",
)


def series_color(index: int) -> QColor:
    """Färgen för serie nummer index; paletten upprepas när serierna är fler."""
    return QColor(SERIES_COLORS[index % len(SERIES_COLORS)])


def device_color(label: str) -> str:
    """Färgen för enhetsraden ur etiketten cuda_device_label ger (TASK-139)."""
    return DEVICE_CUDA_COLOR if label.startswith("Enhet: CUDA") else DEVICE_CPU_COLOR

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
