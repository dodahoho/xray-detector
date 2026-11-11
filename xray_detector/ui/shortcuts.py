"""Synliga tangentbordsgenvägar (TASK-41).

Mnemonik skrivs med & i etiketten: Qt visar bokstaven understruken och ger
Alt+bokstav. Genvägar som inte kan bli mnemonik, eller där bokstaven saknas i
etiketten, visas i stället inom parentes.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


def mnemonic(label: str, letter: str) -> str:
    """Etikett med & före bokstaven, så Qt ger understrykning och Alt+bokstav."""
    index = label.lower().find(letter.lower())
    if index < 0:
        return label
    return f"{label[:index]}&{label[index:]}"


def with_hint(label: str, hint: str) -> str:
    """Etikett med genvägen inom parentes när den inte är en mnemonik."""
    return f"{label} ({hint})"


def bind_shortcut(widget, key: str, slot) -> QShortcut:
    """Genväg som bara är aktiv när widgetens vy syns.

    WindowShortcut-kontexten kräver att widgeten är synlig och ligger i det
    aktiva fönstret, så en genväg på en inaktiv flik utlöses inte.
    """
    shortcut = QShortcut(QKeySequence(key), widget)
    shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
    shortcut.activated.connect(slot)
    return shortcut
