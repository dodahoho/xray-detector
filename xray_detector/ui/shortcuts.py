"""Synliga tangentbordsgenvägar (TASK-41, TASK-116).

Mnemonik skrivs med & i etiketten: Qt visar bokstaven understruken och ger
Alt+bokstav. Genvägar som inte kan bli mnemonik, eller där bokstaven saknas i
etiketten, visas i stället inom parentes.

Enter, Esc och Del/Backspace betyder samma sak i varje vy (TASK-116): Enter kör
vyens standardåtgärd, Esc avbryter och Del/Backspace tar bort det markerade.
Tangenterna ligger här, så en vy som får en standardåtgärd binder samma tangenter
som de andra. Ett fält som har en egen Enter-åtgärd, som klassrutan i
annoteringsvyn, behåller tangenten med bind_field_enter.
"""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeySequence, QShortcut

#: Enter, både huvudtangenten och den på det numeriska tangentbordet
DEFAULT_KEYS = ("Return", "Enter")
#: Del och Backspace tar bort det markerade
DELETE_KEYS = ("Del", "Backspace")
#: Tangentkoderna som hör till DEFAULT_KEYS
ENTER_CODES = (Qt.Key.Key_Return, Qt.Key.Key_Enter)


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


class _FieldEnterFilter(QObject):
    """Låter Enter i ett fält köra fältets egen åtgärd (TASK-116).

    Vyns Enter-genväg är en WindowShortcut och vinner annars över fältet. Filtret
    accepterar fältets ShortcutOverride för Enter, så genvägen inte utlöses, och
    kör i stället sloten på tangenttryckningen.
    """

    def __init__(self, slot, parent=None) -> None:
        super().__init__(parent)
        self.slot = slot

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.ShortcutOverride:
            if event.key() in ENTER_CODES:
                event.accept()
                return True
            return False
        if event.type() == QEvent.Type.KeyPress and event.key() in ENTER_CODES:
            self.slot()
            return True
        return False


def bind_field_enter(field, slot) -> QObject:
    """Enter i fältet kör fältets egen åtgärd i stället för vyens (TASK-116).

    Används där Enter betyder något annat än vyens standardåtgärd, som att spara
    klassnamnet i annoteringsvyns klassruta.
    """
    handler = _FieldEnterFilter(slot, field)
    field.installEventFilter(handler)
    return handler
