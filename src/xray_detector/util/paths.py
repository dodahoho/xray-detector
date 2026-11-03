from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xray_detector.config import AppConfig


@dataclass(frozen=True)
class AppPaths:
    data_root: Path

    @classmethod
    def from_config(cls, config: AppConfig) -> "AppPaths":
        root = Path(config.app.data_dir).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root
        return cls(root.resolve())

    @property
    def datasets(self) -> Path:
        return self.data_root / "datasets"

    @property
    def models(self) -> Path:
        return self.data_root / "models"

    @property
    def exports(self) -> Path:
        return self.data_root / "exports"

    @property
    def pending(self) -> Path:
        return self.data_root / "pending"

    @property
    def training(self) -> Path:
        return self.data_root / "training"

    @property
    def logs(self) -> Path:
        return self.data_root / "logs"

    def ensure(self) -> "AppPaths":
        for path in (
            self.data_root,
            self.datasets,
            self.models,
            self.exports,
            self.pending,
            self.training,
            self.logs,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def dataset_dir(self, dataset_id: str) -> Path:
        return self.datasets / dataset_id

    def model_dir(self, model_id: str) -> Path:
        return self.models / model_id
