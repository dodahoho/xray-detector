"""Application configuration loading and persistence."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"
DEFAULT_MODELS_PATH = PROJECT_ROOT / "config" / "models.yaml"


def _user_config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "XrayDetector"


def user_config_path() -> Path:
    override = os.environ.get("XRAY_DETECTOR_CONFIG")
    if override:
        return Path(override)
    return _user_config_dir() / "config.yaml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        elif value is not None:
            result[key] = value
    return result


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@dataclass
class AppSettings:
    dataset: str = "default"
    default_model: str = "yolo26n"
    language: str = "sv"
    data_root: str | None = None
    log_level: str = "INFO"


@dataclass
class UISettings:
    fullscreen: bool = False
    kiosk: bool = False
    exit_shortcut: str = "Ctrl+Shift+Q"
    show_cursor: bool = True
    start_detection_on_launch: bool = True


@dataclass
class VideoSourceSettings:
    type: str = "device"
    index: int = 0
    file: str | None = None
    width: int = 1920
    height: int = 1080
    fps: int = 30
    backend: str = "auto"
    loop_file: bool = True


@dataclass
class VideoSettings:
    cam0: VideoSourceSettings = field(default_factory=lambda: VideoSourceSettings(index=0))
    cam1: VideoSourceSettings = field(default_factory=lambda: VideoSourceSettings(index=1))


@dataclass
class DetectionSettings:
    conf: float = 0.25
    iou: float = 0.45
    imgsz: int = 640
    device: str = "cuda:0"
    half: bool = True
    max_fps: int = 30


@dataclass
class DatasetSettings:
    jpeg_quality: int = 95
    min_box_size: int = 5
    train_split: float = 0.8
    val_split: float = 0.2
    split_seed: int = 42


@dataclass
class TrainingDefaults:
    pause_detection: bool = True
    epochs: int = 100
    batch: int = 8
    imgsz: int = 640
    learning_rate: float = 0.01
    patience: int = 50
    workers: int = 4


@dataclass
class AppConfig:
    app: AppSettings = field(default_factory=AppSettings)
    ui: UISettings = field(default_factory=UISettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    dataset: DatasetSettings = field(default_factory=DatasetSettings)
    training: TrainingDefaults = field(default_factory=TrainingDefaults)
    project_root: Path = field(default=PROJECT_ROOT)
    config_path: Path = field(default_factory=user_config_path)

    @classmethod
    def load(cls, config_path: Path | None = None) -> AppConfig:
        defaults = _read_yaml(DEFAULT_CONFIG_PATH)
        path = config_path or user_config_path()
        user = _read_yaml(path)
        merged = _deep_merge(defaults, user)
        cfg = cls._from_dict(merged)
        cfg.config_path = path
        return cfg

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> AppConfig:
        app = AppSettings(**data.get("app", {}))
        ui = UISettings(**data.get("ui", {}))
        video_data = data.get("video", {})
        video = VideoSettings(
            cam0=VideoSourceSettings(**video_data.get("cam0", {})),
            cam1=VideoSourceSettings(**video_data.get("cam1", {})),
        )
        detection = DetectionSettings(**data.get("detection", {}))
        dataset = DatasetSettings(**data.get("dataset", {}))
        training = TrainingDefaults(**data.get("training", {}))
        return cls(
            app=app,
            ui=ui,
            video=video,
            detection=detection,
            dataset=dataset,
            training=training,
        )

    @property
    def data_root(self) -> Path:
        if self.app.data_root:
            return Path(self.app.data_root).expanduser()
        return self.project_root / "data"

    @property
    def datasets_dir(self) -> Path:
        return self.data_root / "datasets"

    @property
    def models_dir(self) -> Path:
        return self.data_root / "models"

    @property
    def exports_dir(self) -> Path:
        return self.data_root / "exports"

    @property
    def runs_dir(self) -> Path:
        return self.data_root / "training_runs"

    @property
    def logs_dir(self) -> Path:
        return self.data_root / "logs"

    @property
    def drafts_dir(self) -> Path:
        return self.data_root / "drafts"

    def ensure_dirs(self) -> None:
        for path in (
            self.datasets_dir,
            self.models_dir,
            self.exports_dir,
            self.runs_dir,
            self.logs_dir,
            self.drafts_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "app": asdict(self.app),
            "ui": asdict(self.ui),
            "video": {
                "cam0": asdict(self.video.cam0),
                "cam1": asdict(self.video.cam1),
            },
            "detection": asdict(self.detection),
            "dataset": asdict(self.dataset),
            "training": asdict(self.training),
        }

    def save(self, path: Path | None = None) -> Path:
        target = path or self.config_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(self.to_dict(), handle, sort_keys=False, allow_unicode=True)
        return target


def load_model_config(path: Path | None = None) -> dict[str, Any]:
    return _read_yaml(path or DEFAULT_MODELS_PATH)
