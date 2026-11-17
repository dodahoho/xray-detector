import os
from dataclasses import dataclass, field
from pathlib import Path

# Projektroten ur paketets placering, så modell- och loggkatalogerna hittas även
# när appen startas från en annan arbetskatalog (TASK-50, TASK-51).
PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Miljövariabel som pekar loggarna någon annanstans, t.ex. i testsviten (TASK-99).
LOGS_DIR_ENV = "XRAY_LOGS_DIR"


def default_logs_dir() -> Path:
    """Loggkatalogen: XRAY_LOGS_DIR om den är satt, annars projektets logs/."""
    override = os.environ.get(LOGS_DIR_ENV)
    return Path(override) if override else PROJECT_ROOT / "logs"


@dataclass
class AppConfig:
    data_dir: Path = field(default_factory=lambda: Path.home() / ".xray-detector")
    models_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "models")
    logs_dir: Path = field(default_factory=default_logs_dir)
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
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

