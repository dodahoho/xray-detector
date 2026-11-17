"""Synliga tangentbordsgenvägar (TASK-41, TASK-116).

Mnemonik skrivs med & i etiketten: Qt visar bokstaven understruken och ger
Alt+bokstav. Genvägar som inte kan bli mnemonik, eller där bokstaven saknas i
etiketten, visas i stället inom parentes.

Enter, Esc och Del/Backspace betyder samma sak i varje vy (TASK-116): Enter kör
vyens standardåtgärd, Esc avbryter och Del/Backspace tar bort det markerade.
Tangenterna ligger här, så en vy som får en standardåtgärd binder samma tangenter
som de andra.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

#: Enter, både huvudtangenten och den på det numeriska tangentbordet
DEFAULT_KEYS = ("Return", "Enter")
#: Del och Backspace tar bort det markerade
DELETE_KEYS = ("Del", "Backspace")


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


def bind_default_action(widget, slot) -> list[QShortcut]:
    """Enter kör vyens standardåtgärd, som dialogens standardknapp (TASK-116).

    Genvägen binds utan filter, så den vinner över vyens fält. Bind den bara i
    vyer där Enter betyder en åtgärd: i de andra vyerna ska Enter fortsätta att
    bekräfta fältet man skriver i.
    """
    return [bind_shortcut(widget, key, slot) for key in DEFAULT_KEYS]


def bind_delete(widget, slot) -> list[QShortcut]:
    """Del och Backspace tar bort det markerade i vyn (TASK-116).

    Ett fält som redigeras behåller Backspace, så ett datum- eller textfält
    fortsätter att sudda i stället för att ta bort det markerade.
    """
    return [bind_shortcut(widget, key, slot) for key in DELETE_KEYS]
