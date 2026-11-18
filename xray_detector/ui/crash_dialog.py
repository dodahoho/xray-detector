"""Global kraschdialog via excepthook (TASK-16).

Otackade undantag i GUI-traden ska inte bara forsvinna i en konsol som
anvandaren aldrig ser: install_exception_dialog() erstatter sys.excepthook
med en krok som loggar felet (rotationsloggen fran TASK-15), visar en
QMessageBox med felnamn, meddelande och full traceback som detaljtext,
skriver tracebacken till stderr for konsolkorningar - och luter sedan
appen fortsatta istallet for en tyst krasch.

Ctrl+C ar ett avsiktligt avbrott, inte en krasch: kroken hoppar over
KeyboardInterrupt, loggar det som INFO och stanger appen (TASK-100).
"""

import logging
import sys
import traceback

from PySide6 import QtWidgets


def _quit_on_interrupt(exc_type, exc_value, exc_tb) -> None:
    """Avslutar appen utan kraschdialog nar anvandaren tryckt Ctrl+C (TASK-100).

    Loggas som INFO sa att den enda ERROR-raden i loggen forblir ett verkligt
    fel. Utan Qt-app (konsolkorning) tar Pythons egen krok over.
    """
    logging.getLogger("xray").info("Avbryter: Ctrl+C")
    try:
        app = QtWidgets.QApplication.instance()
    except Exception:
        app = None
    if app is None:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    app.quit()


def excepthook_with_dialog(exc_type, exc_value, exc_tb) -> None:
    if exc_type is not None and issubclass(exc_type, KeyboardInterrupt):
        _quit_on_interrupt(exc_type, exc_value, exc_tb)
        return
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.getLogger("xray").error("Ohanterat undantag:\n%s", text)
    print(text, file=sys.stderr)
    try:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            box = QtWidgets.QMessageBox()
            box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            box.setWindowTitle("Ov\u00e4ntat fel")
            box.setText(f"{exc_type.__name__}: {exc_value}")
            box.setInformativeText("Felet har loggats. Kontakta support om det upprepas.")
            box.setDetailedText(text)
            box.exec()
    except Exception:
        # kraschhanteraren far aldrig sjalv krascha; felet ar redan loggat
        pass


def install_exception_dialog() -> None:
    """Installerar kraschkroken (anropa efter QApplication skapats)."""
    sys.excepthook = excepthook_with_dialog


def restore_default_excepthook() -> None:
    """Aterstaller Pythons standardkrok (testhygien)."""
    sys.excepthook = sys.__excepthook__
