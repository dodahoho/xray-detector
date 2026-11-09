from xray_detector.domain.training import TrainConfig
from xray_detector.infrastructure.training.trainer import TrainingWorker


class TrainingService:
    """Skapar och avbryter träningsjobb som körs i träningens delprocess."""

    def __init__(self) -> None:
        self.active_worker: TrainingWorker | None = None

    def create_worker(self, config: TrainConfig) -> TrainingWorker:
        self.active_worker = TrainingWorker(config)
        return self.active_worker

    def cancel(self) -> None:
        if self.active_worker is not None:
            self.active_worker.cancel()
