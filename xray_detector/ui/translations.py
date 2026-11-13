"""Svenska texter i Qt:s egna dialoger (TASK-83).

Appens egna strängar är skrivna på svenska, men standardknapparna i
QMessageBox, QDialogButtonBox och QInputDialog kommer från Qt och står på
engelska utan en översättning. qtbase_sv.qm följer med PySide6, så appen
behöver bara ladda den.

Translatorn måste leva så länge appen kör: Qt slår upp texten när en
standardknapp skapas, och en translator som städats bort ger engelska knappar
igen.
"""

from PySide6.QtCore import QLibraryInfo, QTranslator

TRANSLATION = "qtbase_sv"


def install_swedish_translations(app) -> QTranslator | None:
    """Laddar Qt:s svenska översättning; None när den inte finns.

    Translatorn får appen som förälder och lever därför lika länge som den.
    Den returneras också, så en anropare kan ta bort den igen: testerna gör det
    för att övriga tester ska se Qt:s originaltexter.
    """
    translator = QTranslator(app)
    directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if not translator.load(TRANSLATION, directory):
        return None
    return translator if app.installTranslator(translator) else None
