"""Training configuration and result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class TrainingParams:
    epochs: int = 100
    batch: int = 8
    imgsz: int = 640
    learning_rate: float = 0.01
    patience: int = 50
    workers: int = 4
    device: str = "cuda:0"


@dataclass
class TrainingRequest:
    dataset_name: str
    dataset_version: str
    base_model_id: str
    base_model_path: str
    family: str
    params: TrainingParams
    run_name: str = "run"
    pause_detection: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrainingResult:
    success: bool
    message: str
    model_dir: str | None = None
    manifest: dict = field(default_factory=dict)
