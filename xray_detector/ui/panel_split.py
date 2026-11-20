"""Två bildpaneler sida vid sida med justerbar ram och maximera-knapp (TASK-164).

Både detektions- och annoteringsvyn visar två bildkällor bredvid varandra. Här
ligger den gemensamma ytan: en QSplitter som ger en ram i mitten att dra i, och
en knapp per panel som maximerar panelen och fäller ihop den andra. Knappen
ligger i panelen den hör till, så den sitter där bilden syns.

Den som maximerar en panel får tillbaka båda bilderna med samma storlekar som
före maximeringen, så en storlek man dragit fram inte tappas på vägen. Ett
maximerat läge är alltså inte samma sak som att dra ramen till kanten: ramen
går bara att dra så långt att båda panelerna fortfarande syns.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QSplitter, QWidget

from xray_detector.ui.tool_icons import maximize_icon, restore_icon

#: Ramen mellan panelerna; bredare än Qt:s standard, så den är lätt att greppa.
HANDLE_WIDTH = 8
MAXIMIZE_TOOLTIP = "Maximera bilden och fäll ihop den andra"
RESTORE_TOOLTIP = "Visa båda bilderna igen"


class PanelSplit(QSplitter):
    """De två bildpanelerna med en justerbar ram och en maximera-knapp var.

    Panelerna läggs in med add_panel(), som också kopplar panelens knapp. Bara
    en panel i taget kan vara maximerad, och knapparna hålls i takt så den
    panel som inte syns aldrig ser vald ut.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        # panelerna får inte dras ihop till noll, så en bild aldrig försvinner
        self.setChildrenCollapsible(False)
        self.setHandleWidth(HANDLE_WIDTH)
        self._panels: list[QWidget] = []
        self._buttons: list[QPushButton] = []
        self._maximized: int | None = None
        self._saved_sizes: list[int] = []

    def add_panel(self, panel: QWidget, button: QPushButton) -> None:
        """Lägger panelen bredvid de tidigare och kopplar dess maximera-knapp."""
        index = len(self._panels)
        self.addWidget(panel)
        self._panels.append(panel)
        self._buttons.append(button)
        button.setCheckable(True)
        button.setIcon(maximize_icon())
        button.setToolTip(MAXIMIZE_TOOLTIP)
        button.clicked.connect(lambda _checked=False, index=index: self._on_clicked(index))

    def maximized(self) -> int | None:
        """Index för den maximerade panelen, eller None när båda syns."""
        return self._maximized

    def maximize(self, index: int) -> None:
        """Visar bara panelen med det indexet."""
        if self._maximized == index:
            return
        if self._maximized is None:
            sizes = self.sizes()
            # före första layouten är storlekarna noll och inget att spara
            if all(size > 0 for size in sizes):
                self._saved_sizes = sizes
        self._maximized = index
        self._apply()

    def restore(self) -> None:
        """Visar båda panelerna igen, med storlekarna de hade före maximeringen."""
        if self._maximized is None:
            return
        self._maximized = None
        self._apply()

    def _on_clicked(self, index: int) -> None:
        if self._maximized == index:
            self.restore()
        else:
            self.maximize(index)

    def _apply(self) -> None:
        for position, panel in enumerate(self._panels):
            panel.setVisible(self._maximized is None or position == self._maximized)
        for position, button in enumerate(self._buttons):
            selected = position == self._maximized
            button.setChecked(selected)
            button.setIcon(restore_icon() if selected else maximize_icon())
            button.setToolTip(RESTORE_TOOLTIP if selected else MAXIMIZE_TOOLTIP)
        if self._maximized is None and self._saved_sizes:
            self.setSizes(self._saved_sizes)
