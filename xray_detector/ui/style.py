"""Gemensamma mått för GUI-element (TASK-49).

Knapparna ska se likadana ut i varje vy, så måtten ligger här i stället för i
vyerna: en ändring slår igenom överallt. Ett element som behöver egna mått
skickar height= eller width= till button(), eller använder apply_metrics() på
en widget som Qt har skapat, som dialogens standardknappar.
"""

from PySide6.QtWidgets import QPushButton, QWidget

BUTTON_HEIGHT = 32
ICON_BUTTON_WIDTH = 36


def apply_metrics(
    widget: QWidget,
    *,
    height: int | None = BUTTON_HEIGHT,
    width: int | None = None,
) -> QWidget:
    """Ger widgeten de gemensamma måtten; None lämnar måttet till Qt."""
    if height is not None:
        widget.setFixedHeight(height)
    if width is not None:
        widget.setFixedWidth(width)
    return widget


def button(
    text: str,
    *,
    parent: QWidget | None = None,
    height: int | None = BUTTON_HEIGHT,
    width: int | None = None,
    primary: bool = False,
) -> QPushButton:
    """Knapp med de gemensamma måtten.

    primary markerar vyens huvudåtgärd med fet stil i stället för en högre
    knapp, så raden håller samma höjd som övriga knappar.
    """
    widget = QPushButton(text, parent)
    apply_metrics(widget, height=height, width=width)
    if primary:
        font = widget.font()
        font.setBold(True)
        widget.setFont(font)
    return widget
