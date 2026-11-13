"""Gemensamma mått för GUI-element (TASK-49, TASK-82).

Knapparna ska se likadana ut i varje vy, så måtten ligger här i stället för i
vyerna: en ändring slår igenom överallt. Ett element som behöver egna mått
skickar height= eller width= till button(), eller använder apply_metrics() på
en widget som Qt har skapat, som dialogens standardknappar.

Formulärfält samlas i ett FormCard med en maxbredd, så en dropdown eller ett
textfält inte sträcker sig över hela skärmen.
"""

from PySide6.QtWidgets import QFormLayout, QGroupBox, QPushButton, QWidget

BUTTON_HEIGHT = 32
ICON_BUTTON_WIDTH = 36
# bredden på ett kort med formulärfält respektive med en lista och knapprader
FORM_MAX_WIDTH = 520
LIST_MAX_WIDTH = 640


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


class FormCard(QGroupBox):
    """Kort med rubrik och ett formulär, med en maxbredd (TASK-82).

    Fälten blir aldrig bredare än kortet, så vyns övriga bredd lämnas tom i
    stället för att en dropdown växer över hela skärmen. Kortet läggs till
    vänster i vyn och formuläret ligger i self.form.
    """

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self.setMaximumWidth(FORM_MAX_WIDTH)
        self.form = QFormLayout(self)
