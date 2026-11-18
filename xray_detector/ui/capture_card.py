"""Kort och tumnaglar i datasetvyn (TASK-65, TASK-145).

Widgetarna låg tidigare i dataset_view.py och flyttades hit när vyfilen delades
upp. Kortet fångar klick på hela ytan, medan tumnageln har egna klick- och
dubbelklickssignaler.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from xray_detector.ui.colors import (
    IDLE_BACKGROUND,
    IDLE_BORDER,
    SELECTED_BACKGROUND,
    SELECTED_BORDER,
)

THUMB_BORDER = 3


class CaptureCard(QFrame):
    """Kort för en fångst; hela ytan markerar fångsten (TASK-65).

    Thumbnails hanterar sina egna klick, så ett klick på en bild växlar en gång.
    Klick på rubrik, klassmärken och kortets marginal når hit i stället.
    """

    clicked = Signal(object)

    def __init__(self, group_id, parent=None) -> None:
        super().__init__(parent)
        self.group_id = group_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self)


class Thumbnail(QWidget):
    clicked = Signal(object)
    double_clicked = Signal(object)

    def __init__(
        self,
        image_id,
        group_id,
        pixmap: QPixmap,
        pending: bool = False,
        tooltip: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.image_id = image_id
        self.group_id = group_id
        self.pending = pending
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.picture = QLabel()
        self.picture.setPixmap(pixmap)
        self.picture.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.picture)
        self._apply_style()

    def _apply_style(self) -> None:
        """Bara färgen växlar; samma rambredd håller bildens storlek fast (TASK-63)."""
        border = SELECTED_BORDER if self.selected else IDLE_BORDER
        background = SELECTED_BACKGROUND if self.selected else IDLE_BACKGROUND
        self.setStyleSheet(
            f"Thumbnail {{ background: {background}; border: {THUMB_BORDER}px solid {border}; "
            "border-radius: 6px; }"
        )

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._apply_style()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit(self)
