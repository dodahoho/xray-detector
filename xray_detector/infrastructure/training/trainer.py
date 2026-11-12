import sys

from PySide6.QtCore import QObject, QProcess, Signal

from xray_detector.domain.training import TrainConfig
from xray_detector.infrastructure.training.epoch_metrics import (
    ABORT_MARKER,
    EPOCH_MARKER,
    parse_abort_line,
    parse_event_line,
)

TRAINING_MODULE = "xray_detector.infrastructure.training.train_task"


class TrainingWorker(QObject):
    """Startar och bevakar träningsprocessen via QProcess (TASK-6).

    Träningen kör i en separat OS-process; stdout strömmas radvis som
    progress-signaler och cancel() avbryter med terminate() och
    kill()-fallback utan att lämna föräldralösa processer efter appen.

    Partiella rader buffras tills radbrytningen kommer (TASK-44): ultralytics
    skriver en rad i flera delar, och utan bufferten blev varje del en egen
    loggrad. Epokeventen lyfts ut till epoch_metrics så GUI:t slipper parsa
    fri text.
    """

    progress = Signal(str)
    epoch_metrics = Signal(object)
    abort_reason = Signal(str)
    finished_training = Signal(bool, str)

    def __init__(self, config: TrainConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._process: QProcess | None = None
        self._buffer = ""

    def command(self) -> list[str]:
        """Kommandorad för träningsprocessen (testbar)."""
        return [
            sys.executable,
            "-m",
            TRAINING_MODULE,
            "--dataset",
            str(self.config.dataset_yaml),
            "--weights",
            self.config.weights,
            "--output",
            str(self.config.output_dir),
            "--epochs",
            str(self.config.epochs),
            "--imgsz",
            str(self.config.imgsz),
            "--batch",
            str(self.config.batch),
            "--family",
            str(self.config.family),
            "--overfitting-guard",
            "on" if self.config.overfitting_guard else "off",
        ]

    def start(self) -> None:
        self._buffer = ""
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)
        command = self.command()
        self._process.start(command[0], command[1:])

    def _on_stdout(self) -> None:
        if self._process is None:
            return
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._buffer += data
        *lines, self._buffer = self._buffer.split("\n")
        for line in lines:
            self._emit_line(line.rstrip("\r"))

    def _emit_line(self, line: str) -> None:
        """Delar upp raden på vagnreturer och lyfter ut strukturerade event.

        Ultralytics tqdm skriver sin förloppsrad utan radbrytning, så ett
        epokevent kan hamna mitt i en sådan rad. Markören söks därför i hela
        texten, och det som står före den loggas som vanlig utmatning.
        """
        for part in line.split("\r"):
            self._emit_part(part)

    def _emit_part(self, part: str) -> None:
        if not part.strip():
            return
        prefix, event = _split_at_marker(part, EPOCH_MARKER)
        if event is not None:
            metrics = parse_event_line(event)
            if metrics is not None:
                self._emit_progress(prefix)
                self.epoch_metrics.emit(metrics)
                self.progress.emit(metrics.summary())
                return
        prefix, event = _split_at_marker(part, ABORT_MARKER)
        if event is not None:
            reason = parse_abort_line(event)
            if reason is not None:
                self._emit_progress(prefix)
                self.abort_reason.emit(reason)
                self.progress.emit(f"Träningen avbröts: {reason}")
                return
        self._emit_progress(part)

    def _emit_progress(self, text: str) -> None:
        if text.strip():
            self.progress.emit(text.rstrip())

    def _on_finished(self, exit_code: int, _status) -> None:
        if self._buffer.strip():
            self._emit_line(self._buffer.rstrip("\r"))
        self._buffer = ""
        ok = exit_code == 0
        self.finished_training.emit(ok, f"Träning avslutad (kod {exit_code})")

    def is_running(self) -> bool:
        return (
            self._process is not None
            and self._process.state() != QProcess.ProcessState.NotRunning
        )

    def cancel(self) -> None:
        """Avbryter processen: först terminate(), sedan kill() som fallback."""
        if not self.is_running():
            return
        self._process.terminate()
        if not self._process.waitForFinished(3000):
            self._process.kill()
            self._process.waitForFinished(2000)


def _split_at_marker(text: str, marker: str) -> tuple[str, str | None]:
    """Delar texten vid markören: (före markören, från markören)."""
    index = text.find(marker)
    if index < 0:
        return text, None
    return text[:index], text[index:]
