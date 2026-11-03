from __future__ import annotations

from datetime import datetime, time
from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal

from src.core.models_schema import TrainingConfig


class TrainingScheduler(QObject):
    """Övervakar inaktivitet och nattfönster för att starta köade träningsjobb automatiskt."""

    trigger_scheduled_training = Signal(object)  # TrainingConfig
    status_updated = Signal(str)

    def __init__(
        self,
        inactivity_timeout_minutes: int = 30,
        night_start_str: str = "23:00",
        night_end_str: str = "05:00",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.inactivity_timeout_seconds = max(10, inactivity_timeout_minutes * 60)
        self.night_start = self._parse_time(night_start_str, time(23, 0))
        self.night_end = self._parse_time(night_end_str, time(5, 0))

        self.last_activity_at: datetime = datetime.now()
        self.queued_job: Optional[TrainingConfig] = None

        self._timer = QTimer(self)
        self._timer.setInterval(5000)  # Kontrollera var 5:e sekund
        self._timer.timeout.connect(self._check_schedule)
        self._timer.start()

    @staticmethod
    def _parse_time(val: str, fallback: time) -> time:
        try:
            parts = val.strip().split(":")
            return time(int(parts[0]), int(parts[1]))
        except Exception:
            return fallback

    def record_user_activity(self) -> None:
        """Anropas vid mus-/tangentbordsaktivitet i GUI."""
        self.last_activity_at = datetime.now()

    def queue_job(self, config: TrainingConfig) -> None:
        self.queued_job = config
        if config.schedule_mode == "night":
            self.status_updated.emit(
                f"Träning köad för nattetid ({self.night_start.strftime('%H:%M')}–{self.night_end.strftime('%H:%M')}) "
                f"med Dataset v{config.dataset_version}"
            )
        elif config.schedule_mode == "inactivity":
            mins = self.inactivity_timeout_seconds // 60
            self.status_updated.emit(
                f"Träning köad vid inaktivitet ({mins} min) med Dataset v{config.dataset_version}"
            )

    def cancel_queued_job(self) -> None:
        self.queued_job = None
        self.status_updated.emit("Ingen schemalagd träning i kö.")

    def is_night_window(self, now: Optional[datetime] = None) -> bool:
        now_dt = now or datetime.now()
        t = now_dt.time()
        if self.night_start <= self.night_end:
            return self.night_start <= t <= self.night_end
        # Fönster över midnatt, t.ex. 23:00 -> 05:00
        return t >= self.night_start or t <= self.night_end

    def is_inactive(self, now: Optional[datetime] = None) -> bool:
        now_dt = now or datetime.now()
        elapsed = (now_dt - self.last_activity_at).total_seconds()
        return elapsed >= self.inactivity_timeout_seconds

    def _check_schedule(self) -> None:
        if self.queued_job is None:
            return

        now = datetime.now()
        job = self.queued_job

        if job.schedule_mode == "night" and self.is_night_window(now):
            self.queued_job = None
            self.status_updated.emit("Startar schemalagd natträning...")
            self.trigger_scheduled_training.emit(job)
        elif job.schedule_mode == "inactivity" and self.is_inactive(now):
            self.queued_job = None
            self.status_updated.emit("Startar träning p.g.a. inaktivitet...")
            self.trigger_scheduled_training.emit(job)
