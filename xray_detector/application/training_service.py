import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from xray_detector.application.background_task import BackgroundTask
from xray_detector.domain.training import (
    NIGHT_END_DEFAULT,
    NIGHT_START_DEFAULT,
    TrainConfig,
    format_clock,
    parse_clock,
)
from xray_detector.infrastructure.training.trainer import TrainingWorker


class TrainingScheduler(QObject):
    """Köar träningsjobb till nattfönster eller efter inaktivitet (TASK-7).

    Pollar var 5:e sekund och startar det köade jobbet via
    TrainingService när villkoret är uppfyllt. Aktivitet rapporteras via
    record_activity() från ett globalt eventfilter i GUI:t.
    """

    status_changed = Signal(str)
    POLL_INTERVAL_MS = 5000

    def __init__(self, service: "TrainingService", parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.mode: str | None = None
        self.config: TrainConfig | None = None
        #: datasetexporten som körs när jobbet faktiskt startar (TASK-151)
        self.export: Callable[[], Path] | None = None
        self._export_task: BackgroundTask | None = None
        self.inactivity_minutes = 30
        self.night_start = NIGHT_START_DEFAULT
        self.night_end = NIGHT_END_DEFAULT
        self._last_activity = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._check)
        self._timer.start()

    def queue_job(
        self,
        config: TrainConfig,
        mode: str,
        export: Callable[[], Path] | None = None,
        inactivity_minutes: int = 30,
        night_start: str = "",
        night_end: str = "",
    ) -> None:
        """Köar ett jobb; exporten sparas och körs först när jobbet startar (TASK-151)."""
        if mode not in ("night", "inactivity"):
            raise ValueError(f"Oköat schema-läge: {mode}")
        self.config = config
        self.mode = mode
        self.export = export
        self.inactivity_minutes = max(1, int(inactivity_minutes))
        self.night_start = parse_clock(night_start, self.night_start)
        self.night_end = parse_clock(night_end, self.night_end)
        self.status_changed.emit(self.queued_status())

    def queued_status(self) -> str:
        if self.mode == "night":
            fönster = f"{format_clock(self.night_start)}–{format_clock(self.night_end)}"
            return f"Träning köad till nattfönstret {fönster}"
        if self.mode == "inactivity":
            return f"Träning köad vid inaktivitet ({self.inactivity_minutes} min)"
        return "Ingen träning köad"

    def has_queued(self) -> bool:
        return self.mode is not None

    def cancel(self) -> None:
        if self.mode is not None:
            self.mode = None
            self.config = None
            self.export = None
            self.status_changed.emit("Köat träningsjobb avbokat")

    def record_activity(self) -> None:
        self._last_activity = time.monotonic()

    def inactivity_seconds(self) -> float:
        return time.monotonic() - self._last_activity

    def night_window_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        current = now.time()
        start, end = self.night_start, self.night_end
        if start <= end:
            return start <= current < end
        # fönster över midnatt, t.ex. 23:00-05:00
        return current >= start or current < end

    def condition_met(self) -> bool:
        if self.mode == "night":
            return self.night_window_active()
        if self.mode == "inactivity":
            return self.inactivity_seconds() >= self.inactivity_minutes * 60
        return False

    def _check(self) -> None:
        if self.mode is None or self._export_task is not None:
            return
        active = self.service.active_worker
        if active is not None and active.is_running():
            return
        if not self.condition_met():
            return
        config = self.config
        export = self.export
        self.mode = None
        self.config = None
        self.export = None
        self.status_changed.emit("Schemalagt villkor uppfyllt – startar träning")
        self._start(config, export)

    def _start(self, config: TrainConfig, export: Callable[[], Path] | None) -> None:
        """Exporterar datasetet i bakgrunden och startar sedan träningen (TASK-151).

        Exporten låg tidigare i klickögonblicket, så ett schemalagt jobb tränade
        på de annoteringar som fanns när det köades.
        """
        if export is None:
            self.service.create_worker(config)
            return
        task = BackgroundTask(export)
        task.succeeded.connect(lambda path: self._on_exported(config, path))
        task.failed.connect(
            lambda message: self.status_changed.emit(
                f"Kunde inte exportera datasetet: {message}"
            )
        )
        task.finished.connect(self._on_export_finished)
        self._export_task = task
        task.start()

    def _on_exported(self, config: TrainConfig, path) -> None:
        config.dataset_yaml = Path(path)
        self.service.create_worker(config)

    def _on_export_finished(self) -> None:
        self._export_task = None


class TrainingService(QObject):
    """Skapar och bevakar träningsjobb; äger schemaläggaren."""

    worker_created = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.active_worker: TrainingWorker | None = None
        self._scheduler: TrainingScheduler | None = None

    def scheduler(self) -> TrainingScheduler:
        if self._scheduler is None:
            self._scheduler = TrainingScheduler(self)
        return self._scheduler

    def create_worker(self, config: TrainConfig) -> TrainingWorker:
        self.active_worker = TrainingWorker(config)
        self.worker_created.emit(self.active_worker)
        return self.active_worker

    def cancel(self) -> None:
        if self.active_worker is not None:
            self.active_worker.cancel()
