"""Initiering av konfiguration och loggning (TASK-15).

Appen laser en valfri config.yaml i datakatalogen (eller arbetskatalogen)
som overrider AppConfig-defaults, och startar loggning med filrotation
under datakatalogens logs/ via stdlib logging (ingen extra dependency).
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from xray_detector.domain.config import AppConfig


def _parse_scalar(value):
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes"):
            return True
        if lowered in ("false", "no"):
            return False
        try:
            return float(value) if "." in lowered else int(value)
        except ValueError:
            return value
    return value


def apply_yaml_overrides(config: AppConfig, yaml_path: Path) -> bool:
    """Tillämpar klasser/trösklar från en enkel YAML-fil.

    Endast en liten, väldefinierad delmängd nycklar stöds:
      classes: [a, b, c]
      default_model: yolo26m
      confidence_threshold: 0.4

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
        if key == "classes" and raw.startswith("[") and raw.endswith("]"):
            config.classes = [part.strip().strip("'\"") for part in raw[1:-1].split(",") if part.strip()]
        elif key == "default_model" and raw:
            config.default_model = str(raw).strip("'\"")
        elif key == "confidence_threshold" and raw:
            try:
                config.confidence_threshold = float(raw)
            except ValueError:
                continue
        elif key in ("data_dir",) and raw:
            config.data_dir = Path(str(raw).strip("'\""))
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


def setup_logging(data_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Rotationsloggnings till <data_dir>/logs/app.log; returnerar root-loggern."""
    log_dir = Path(data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(level)
    return logging.getLogger("xray")
