"""Tredjepartens loggrar in i app.log (TASK-98, TASK-143).

Ligger i infrastructure så detektorerna kan fånga rfdetr:s loggrar utan att
importera application. Med fångsten i application blev beroendet
infrastructure -> application cykliskt.
"""

import logging

#: Tredjepartsloggrar vars rader ska nå app.log (TASK-98). rfdetr sätter
#: propagate=False och egna stream-handlers vid import, så utan detta stannar
#: dess rader i konsolen.
CAPTURED_LOGGERS = (
    "rfdetr",
    "rf-detr",
    "ultralytics",
    "torch",
    "transformers",
    "lightning",
    "pytorch_lightning",
    "timm",
    "supervision",
    "huggingface_hub",
    "PIL",
    "matplotlib",
    "urllib3",
)

#: Loggrar som bara skriver brus. comtypes stod för 41 % av app.log (TASK-98).
NOISY_LOGGERS = ("comtypes",)
NOISY_LEVEL = logging.WARNING


def _matches(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes)


def capture_third_party_logs() -> None:
    """Låter tredjepartens rader nå app.log och tystar renodlat brus (TASK-98).

    Python-varningar från torch, transformers och rfdetr går annars bara till
    stderr, eftersom logging.captureWarnings aldrig anropas. rfdetr sätter
    dessutom propagate=False på sina loggrar vid import. Raderna behåller sin
    egen logger i %(name)s, så de går att skilja från appens xray-rader.

    Idempotent: anropas från setup_logging() och igen efter import rfdetr,
    eftersom rfdetr skapar sina loggrar först då.
    """
    # captureWarnings är en global engångsflagga: har något återställt
    # warnings.showwarning (t.ex. pytest:s catch_warnings) blir ett nytt
    # captureWarnings(True) verkningslöst. Nollställ först så fångsten alltid tar.
    logging.captureWarnings(False)
    logging.captureWarnings(True)
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if not isinstance(logger, logging.Logger):
            continue
        if _matches(name, CAPTURED_LOGGERS):
            logger.propagate = True
        if _matches(name, NOISY_LOGGERS):
            logger.setLevel(NOISY_LEVEL)
    # prefixet självt också, så loggrar som skapas senare ärver nivån
    for prefix in NOISY_LOGGERS:
        logging.getLogger(prefix).setLevel(NOISY_LEVEL)
