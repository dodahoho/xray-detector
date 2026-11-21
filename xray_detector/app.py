import ctypes
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThreadPool, qInstallMessageHandler
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from xray_detector.application.app_config import (
    config_values,
    load_config_with_yaml,
    setup_logging,
)
from xray_detector.ui.crash_dialog import install_exception_dialog
from xray_detector.ui.main_window import MainWindow
from xray_detector.ui.translations import install_swedish_translations

ICON_PATH = Path(__file__).parent / "ui" / "assets" / "app.ico"
APP_USER_MODEL_ID = "xray-detector"
#: Tolken läser flaggan när den startar, så den sätts i miljön för
#: barnprocesserna och slås på med en omstart när appen startats utan den
#: (TASK-173).
UTF8_ENV = "PYTHONUTF8"
#: Markör som gör att omstarten sker högst en gång, även om kommandoraden
#: själv stänger av UTF-8-läget med -X utf8=0.
RESTARTED_ENV = "XRAY_UTF8_RESTARTED"
#: Hur länge avslutet väntar in Qt:s trådpool innan processen avslutas ändå.
SHUTDOWN_TIMEOUT_MS = 5000
#: Hur länge vakt-tråden väntar på att destructorerna ska bli klara.
FORCE_EXIT_SECONDS = 3.0


def _install_message_filter() -> None:
    def handler(mode, context, message) -> None:
        if "CreateFontFaceFromHDC() failed" in message:
            return
        print(message, file=sys.stderr)

    qInstallMessageHandler(handler)


def _set_app_user_model_id() -> None:
    """Ger processen en egen identitet i aktivitetsfältet.

    Utan den grupperar Windows fönstret under python.exe och ritar
    Python-ikonen i aktivitetsfältet, oavsett vilken ikon Qt sätter på
    fönstret. Måste köras innan första fönstret skapas.
    """
    if sys.platform != "win32":
        return
    try:
        # ctypes.wintypes finns bara på Windows, så den importeras här
        from ctypes import wintypes  # noqa: PLC0415

        shell32 = ctypes.windll.shell32
        shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
        shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass


def _log_startup(config, config_file, log) -> None:
    """Loggar vilken konfigfil som användes och vilka värden som gäller (TASK-101)."""
    log.info("Startar X-ray detector (konfig: %s)", config_file or "default")
    log.info("Konfigvärden: %s", config_values(config))


def _ensure_utf8_mode(utf8_mode: bool | None = None) -> None:
    """Ser till att appen och processerna den startar läser text som UTF-8 (TASK-173).

    Ett klassnamn med nationella tecken får inte tolkas som cp1252: då blir
    "löpare" till "lÃ¶pare" i de tränade vikterna, och detektorns klassfilter
    släpper inte igenom någon detektion. PYTHONUTF8 läses när tolken startar,
    så flaggan kan inte slås på under körning. Miljövariabeln sätts därför för
    barnprocesserna (träningen), och processen startas om en gång med samma
    kommandorad när läget är av. Omstarten sker före Qt skapas, så inget
    fönster hinner ritas. Markören i miljön gör att den sker högst en gång,
    även om kommandoraden själv stänger av läget med -X utf8=0.

    Omstarten väntar på den nya processen i stället för att ersätta den med
    os.execv: på Windows lämnar execv kvar en föräldralös process som
    terminalen inte längre väntar på, och då kommer kommandoprompten inte
    tillbaka när appen stängs (TASK-176).

    utf8_mode är läget som ska råda; None läser processens verkliga läge.
    """
    os.environ[UTF8_ENV] = "1"
    active = sys.flags.utf8_mode if utf8_mode is None else utf8_mode
    if active or os.environ.get(RESTARTED_ENV):
        return
    os.environ[RESTARTED_ENV] = "1"
    try:
        result = subprocess.run([sys.executable, *sys.orig_argv[1:]])
    except KeyboardInterrupt:
        sys.exit(130)
    sys.exit(result.returncode)


def _force_exit(code: int) -> None:
    """Avslutar processen om destructorerna inte hinner klart (TASK-175)."""
    time.sleep(FORCE_EXIT_SECONDS)
    os._exit(code)


def _finish(code: int, log: logging.Logger) -> None:
    """Avslutar processen när fönstret är stängt (TASK-175).

    Qt:s globala trådpool väntar in pågående arbete när den rivs, och CUDA:s
    statiska destructorer kan blockera när GPU:n är upptagen. Ingen av dem har
    en tidsgräns, så processen kunde bli kvar efter att fönstret stängts.
    closeEvent har redan synkat inställningarna och väntat in arbetstrådarna,
    så här väntas trådpoolen en kort stund. En vakt-tråd avslutar processen om
    destructorerna ändå inte hinner klart, så en vanlig stängning fortfarande
    städar efter sig.
    """
    if not QThreadPool.globalInstance().waitForDone(SHUTDOWN_TIMEOUT_MS):
        log.warning(
            "Trådpoolen blev inte klar inom %d ms; avslutar processen",
            SHUTDOWN_TIMEOUT_MS,
        )
    log.info("Avslutar: stänger processen")
    logging.shutdown()
    threading.Thread(target=_force_exit, args=(code,), daemon=True).start()


def main() -> int:
    _install_message_filter()
    _set_app_user_model_id()
    app = QApplication(sys.argv)
    # före första fönstret, så Qt:s standardknappar blir svenska direkt (TASK-83)
    install_swedish_translations(app)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    install_exception_dialog()
    app.setApplicationName("X-ray detector")
    config, config_file = load_config_with_yaml(config_dir=None, workdir=Path.cwd())
    config.ensure_dirs()
    log = setup_logging(config.logs_dir)
    _log_startup(config, config_file, log)
    window = MainWindow(config)
    window.show_window()
    code = app.exec()
    _finish(code, log)
    return code


if __name__ == "__main__":
    _ensure_utf8_mode()
    sys.exit(main())
