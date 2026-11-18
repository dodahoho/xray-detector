"""Initiering av konfiguration och loggning (TASK-15, TASK-51, TASK-98).

Appen laser en valfri config.yaml i datakatalogen (eller arbetskatalogen)
som overrider AppConfig-defaults, och startar loggning med filrotation
under projektets logs/ via stdlib logging (ingen extra dependency).
Tredjepartens varningar och loggrader leds in i samma fil, sa loggfilen
visar det som annars bara syntes i konsolen.
"""

import contextlib
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml

from xray_detector.domain.config import PROJECT_ROOT, AppConfig
from xray_detector.infrastructure.logging import capture_third_party_logs

LOG_FORMAT = "%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5


def apply_yaml_overrides(config: AppConfig, yaml_path: Path) -> bool:
    """Tillämpar trösklar och kataloger från en config.yaml.

    Filen tolkas med yaml.safe_load, så listor, citattecken och kommentarer
    hanteras som YAML i stället för av en egen strängparser (TASK-136).
    Nycklarna som stöds är default_model, confidence_threshold samt data_dir,
    models_dir och logs_dir; models_dir och logs_dir tolkas relativa mot
    projektroten.

    Returnerar True om filen fanns och kunde tolkas.
    """
    if not yaml_path.exists():
        return False
    try:
        values = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False
    if values is None:
        values = {}
    if not isinstance(values, dict):
        return False
    if values.get("default_model"):
        config.default_model = str(values["default_model"])
    if values.get("confidence_threshold") is not None:
        with contextlib.suppress(TypeError, ValueError):
            config.confidence_threshold = float(values["confidence_threshold"])
    for key in ("data_dir", "models_dir", "logs_dir"):
        raw = values.get(key)
        if not raw:
            continue
        path = Path(str(raw))
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
