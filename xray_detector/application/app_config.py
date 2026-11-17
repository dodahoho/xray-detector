"""Initiering av konfiguration och loggning (TASK-15, TASK-51, TASK-98).

Appen laser en valfri config.yaml i datakatalogen (eller arbetskatalogen)
som overrider AppConfig-defaults, och startar loggning med filrotation
under projektets logs/ via stdlib logging (ingen extra dependency).
Tredjepartens varningar och loggrader leds in i samma fil, sa loggfilen
visar det som annars bara syntes i konsolen.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from xray_detector.domain.config import PROJECT_ROOT, AppConfig

LOG_FORMAT = "%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5

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


def apply_yaml_overrides(config: AppConfig, yaml_path: Path) -> bool:
    """Tillämpar klasser/trösklar från en enkel YAML-fil.

    Endast en liten, väldefinierad delmängd nycklar stöds:
      classes: [a, b, c]
      default_model: yolo26m
      confidence_threshold: 0.4
      data_dir: /sökväg
      models_dir: /sökväg (relativ tolkas mot projektroten)
      logs_dir: /sökväg (relativ tolkas mot projektroten)

    Returnerar True om filen fanns och kunde tolkas.
    """
    if not yaml_path.exists():
        return False
    try:
        lines = yaml_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if key == "default_model" and raw:
            config.default_model = str(raw).strip("'\"")
        elif key == "confidence_threshold" and raw:
            try:
                config.confidence_threshold = float(raw)
            except ValueError:
                continue
        elif key in ("data_dir", "models_dir", "logs_dir") and raw:
            path = Path(str(raw).strip("'\""))
            if key in ("models_dir", "logs_dir") and not path.is_absolute():
                path = PROJECT_ROOT / path
            setattr(config, key, path)
    return True


def load_config_with_yaml(config_dir: Path | None = None, workdir: Path | None = None) -> tuple[AppConfig, Path | None]:
    """Skapar AppConfig och applicerar eventuell config.yaml.

    Sökordning: config_dir/config.yaml, sedan <workdir>/config.yaml.
    Returnerar (config, sökvägen till den använda filen eller None).
    """
    config = AppConfig()
    candidates = []
    if config_dir is not None:
        candidates.append(Path(config_dir) / "config.yaml")
    if workdir is not None:
        candidates.append(Path(workdir) / "config.yaml")
    for candidate in candidates:
        if apply_yaml_overrides(config, candidate):
            return config, candidate
    config.ensure_dirs()
    return config, None


def config_values(config: AppConfig) -> str:
    """Konfigurationens gällande värden som en loggvänlig rad (TASK-101)."""
    return (
        f"default_model={config.default_model} "
        f"confidence_threshold={config.confidence_threshold} "
        f"data_dir={config.data_dir} models_dir={config.models_dir} "
        f"logs_dir={config.logs_dir}"
    )


def log_path(logs_dir: Path, name: str) -> Path:
    """Sökväg till en loggtyp under logs/, t.ex. log_path(logs_dir, "training").

    En ny loggtyp är bara ett nytt namn; katalog och rotation sköts av
    rotating_handler()/file_logger() (TASK-51).
    """
    return Path(logs_dir) / f"{name}.log"


def rotating_handler(path: Path) -> RotatingFileHandler:
    """Roterande filhandler (1 MB, 5 backups) med appens loggformat."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def file_logger(name: str, path: Path, level: int = logging.INFO) -> logging.Logger:
    """Logger som skriver till en egen loggfil under logs/ (TASK-51).

    Loggern propagerar inte till root, så en loggtyp hamnar bara i sin egen
    fil. Handlern byts ut om sökvägen ändras, så samma namn kan pekas om
    (t.ex. mellan tester) utan att gamla filer fortsätter skrivas.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    target = os.path.abspath(path)
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == target:
            return logger
        logger.removeHandler(handler)
        handler.close()
    logger.addHandler(rotating_handler(path))
    return logger


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


def setup_logging(logs_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Rotationsloggning till <logs_dir>/app.log; returnerar xray-loggern."""
    handler = rotating_handler(log_path(logs_dir, "app"))
    root = logging.getLogger()
    if any(
        isinstance(existing, RotatingFileHandler)
        and existing.baseFilename == handler.baseFilename
        for existing in root.handlers
    ):
        handler.close()
    else:
        root.addHandler(handler)
    root.setLevel(level)
    capture_third_party_logs()
    return logging.getLogger("xray")
