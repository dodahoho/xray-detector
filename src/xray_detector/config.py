from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

APP_NAME = "xray-detector"


@dataclass
class AppSettings:
    language: str = "sv"
    fullscreen: bool = False
    kiosk: bool = False
    hide_cursor: bool = False
    data_dir: str = "data"
    active_dataset: str = "default"


@dataclass
class VideoSettings:
    backend: str = "dshow"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    camera_left: int = 0
    camera_right: int = 1
    preview_fps: int = 30


@dataclass
class DetectionSettings:
    model: str = "yolo11n.pt"
    device: str = "auto"
    confidence: float = 0.25
    iou: float = 0.45
    detection_fps: float = 10.0
    class_filter: list[int] = field(default_factory=list)


@dataclass
class TrainingSettings:
    default_base_model: str = "yolo11n.pt"
    epochs: int = 100
    imgsz: int = 640
    batch: int = 8
    workers: int = 4


@dataclass
class AppConfig:
    app: AppSettings = field(default_factory=AppSettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    training: TrainingSettings = field(default_factory=TrainingSettings)


def default_config() -> AppConfig:
    return AppConfig()


def user_config_path() -> Path:
    override = os.environ.get("XRAY_DETECTOR_CONFIG")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME / "config.toml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Ogiltig konfigurationsfil: {path}")
    return data


def _build_config(data: dict[str, Any]) -> AppConfig:
    config = default_config()
    config.app = AppSettings(**_filtered(AppSettings, data.get("app", {})))
    config.video = VideoSettings(**_filtered(VideoSettings, data.get("video", {})))
    config.detection = DetectionSettings(**_filtered(DetectionSettings, data.get("detection", {})))
    config.training = TrainingSettings(**_filtered(TrainingSettings, data.get("training", {})))
    _validate(config)
    return config


def _filtered(cls: type, values: dict[str, Any]) -> dict[str, Any]:
    allowed = set(cls.__dataclass_fields__)
    return {key: value for key, value in values.items() if key in allowed}


def _validate(config: AppConfig) -> None:
    if config.video.backend not in {"dshow", "msmf", "any"}:
        raise ValueError("video.backend maste vara dshow, msmf eller any")
    if config.video.camera_left == config.video.camera_right:
        raise ValueError("Kamerorna maste ha olika enhetsindex")
    if config.video.width <= 0 or config.video.height <= 0:
        raise ValueError("video.width och video.height maste vara positiva")
    if config.video.fps <= 0 or config.video.preview_fps <= 0:
        raise ValueError("video.fps och video.preview_fps maste vara positiva")
    if not 0.0 <= config.detection.confidence <= 1.0:
        raise ValueError("detection.confidence maste ligga mellan 0 och 1")
    if not 0.0 <= config.detection.iou <= 1.0:
        raise ValueError("detection.iou maste ligga mellan 0 och 1")
    if config.detection.detection_fps <= 0:
        raise ValueError("detection.detection_fps maste vara positiv")
    if config.training.epochs <= 0:
        raise ValueError("training.epochs maste vara positiv")
    if config.training.imgsz <= 0:
        raise ValueError("training.imgsz maste vara positiv")
    if config.training.batch == 0:
        raise ValueError("training.batch far inte vara 0")


def validate_config(config: AppConfig) -> None:
    _validate(config)


def load_config(path: Path | str | None = None) -> AppConfig:
    base = asdict(default_config())
    override = _load_toml(Path(path).expanduser() if path else user_config_path())
    return _build_config(_deep_merge(base, override))


def save_config(config: AppConfig, path: Path | str | None = None) -> Path:
    target = Path(path).expanduser() if path else user_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    lines: list[str] = []

    def write_section(name: str, values: dict[str, Any]) -> None:
        lines.append(f"[{name}]")
        for key, value in values.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")

    for section in ("app", "video", "detection", "training"):
        write_section(section, data[section])
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise TypeError(f"Kan inte skriva TOML-varde av typen {type(value)!r}")
