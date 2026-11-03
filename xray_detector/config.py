"""Konfiguration för xray-detector.

Läser config.yaml och validerar med Pydantic. Alla paths löses relativt
projektets rotkatalog (där config.yaml ligger).
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class StreamConfig(BaseModel):
    index: int = 0
    width: int = 1920
    height: int = 1080
    fps: int = 30


class CaptureConfig(BaseModel):
    backend: Literal["auto", "dshow", "v4l2"] = "auto"
    streams: list[StreamConfig] = Field(default_factory=lambda: [
        StreamConfig(index=0), StreamConfig(index=1)
    ])


class DetectionConfig(BaseModel):
    model_left: str = "models/yolo26n.pt"
    model_right: str = "models/yolo26n.pt"
    conf: float = 0.4
    iou: float = 0.5
    device: int = 0
    half: bool = True
    preprocess: Literal["auto", "none", "invert", "clahe"] = "auto"


class AppConfig(BaseModel):
    fullscreen: bool = True
    kiosk: bool = False


class DatasetConfig(BaseModel):
    root: str = "data/datasets"


class TrainingConfig(BaseModel):
    default_epochs: int = 100
    default_imgsz: int = 640
    default_batch: int = 16
    runs_dir: str = "runs"


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    classes: list[str] = Field(default_factory=lambda: [
        "cigaretter", "cannabis", "kniv", "handgranat"
    ])
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)

    # ---- Path-hjälpare (lösta relativt projektrot) ----
    @property
    def dataset_root(self) -> Path:
        return PROJECT_ROOT / self.dataset.root

    @property
    def models_dir(self) -> Path:
        return PROJECT_ROOT / "models"

    @property
    def runs_dir(self) -> Path:
        return PROJECT_ROOT / self.training.runs_dir

    @property
    def config_path(self) -> Path:
        return PROJECT_ROOT / "config.yaml"


def load_config(path: Path | None = None) -> Config:
    """Ladda config.yaml (eller default) och returnera validerad Config."""
    path = path or PROJECT_ROOT / "config.yaml"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {}
    return Config.model_validate(raw)
