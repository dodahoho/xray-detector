from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict
from PySide6.QtCore import QThread, Signal

from src.core.models_schema import TrainingConfig
from src.ml.model_registry import ModelRegistry


class TrainingWorker(QThread):
    """Kör modellträning i bakgrunden och sparar modellvikterna med samma versionssiffra som datasetet."""

    progress_updated = Signal(int, int, object, str)  # epoch, total_epochs, metrics_dict, log_line
    training_completed = Signal(object)  # TrainedModelInfo
    training_failed = Signal(str)

    def __init__(
        self,
        config: TrainingConfig,
        models_dir: str | Path = "models/trained",
    ) -> None:
        super().__init__()
        self.config = config
        self.models_dir = Path(models_dir)
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def _is_stop_requested(self) -> bool:
        return self._stop_requested

    def _on_progress(self, epoch: int, total_epochs: int, metrics: Dict[str, float], log_line: str) -> None:
        self.progress_updated.emit(epoch, total_epochs, metrics, log_line)

    def run(self) -> None:
        try:
            trainer = ModelRegistry.create_trainer(self.config.model_family)
            date_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
            fam_slug = self.config.model_family.lower().replace("-", "")
            # Sparas med versionssiffra som överensstämmer med det dataset som använts (v{dataset_version})
            out_dir = self.models_dir / f"v{self.config.dataset_version}_{fam_slug}_{date_slug}"

            trained_info = trainer.train(
                config=self.config,
                output_dir=str(out_dir),
                progress_callback=self._on_progress,
                stop_requested=self._is_stop_requested,
            )
            self.training_completed.emit(trained_info)
        except Exception as exc:
            self.training_failed.emit(str(exc))
