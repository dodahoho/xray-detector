import sys

from PySide6.QtCore import QObject, QProcess, Signal

from xray_detector.domain.training import TrainConfig

TRAINING_MODULE = "xray_detector.infrastructure.training.train_task"


class TrainingWorker(QObject):
    """Startar och bevakar träningsprocessen via QProcess (TASK-6).

    Träningen kör i en separat OS-process; stdout strömmas radvis som
    progress-signaler och cancel() avbryter med terminate() och
    kill()-fallback utan att lämna föräldralösa processer efter appen.
    """

    progress = Signal(str)
    finished_training = Signal(bool, str)

    def __init__(self, config: TrainConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._process: QProcess | None = None

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
        ]

    def start(self) -> None:
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
        for line in data.splitlines():
            line = line.rstrip()
            if line:
                self.progress.emit(line)

    def _on_finished(self, exit_code: int, _status) -> None:
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
