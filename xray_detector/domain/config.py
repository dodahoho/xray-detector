from dataclasses import dataclass, field
from pathlib import Path

# Projektroten ur paketets placering, så modellkatalogen hittas även när appen
# startas från en annan arbetskatalog (TASK-50).
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class AppConfig:
    classes: list[str] = field(
        default_factory=lambda: ["cigaretter", "cannabis", "kniv", "pistol"]
    )
    data_dir: Path = field(default_factory=lambda: Path.home() / ".xray-detector")
    models_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "models")
    confidence_threshold: float = 0.4
    default_model: str = "yolo26m"

    @property
    def dataset_dir(self) -> Path:
        return self.data_dir / "datasets"

    @property
    def export_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def trained_dir(self) -> Path:
        """Egentränade modeller; basvikterna ligger direkt i models_dir."""
        return self.models_dir / "trained"

    def ensure_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.dataset_dir,
            self.export_dir,
            self.models_dir,
            self.trained_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    config = AppConfig()
    config.ensure_dirs()
    return config
