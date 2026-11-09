from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    classes: list[str] = field(
        default_factory=lambda: ["cigaretter", "cannabis", "kniv", "pistol"]
    )
    data_dir: Path = field(default_factory=lambda: Path.home() / ".xray-detector")
    confidence_threshold: float = 0.4
    default_model: str = "yolo26m"

    @property
    def dataset_dir(self) -> Path:
        return self.data_dir / "datasets"

    @property
    def export_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.dataset_dir, self.export_dir, self.models_dir):
            path.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    config = AppConfig()
    config.ensure_dirs()
    return config
