import subprocess
import sys

from PySide6.QtCore import QThread, Signal

from xray_detector.domain.training import TrainConfig

TRAINING_MODULE = "xray_detector.infrastructure.training.train_task"


class TrainingWorker(QThread):
    progress = Signal(str)
    finished_training = Signal(bool, str)

    def __init__(self, config: TrainConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._process: subprocess.Popen | None = None

    def command(self) -> list[str]:
        """Kommandorad for träningsprocessen (testbar)."""
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

    def run(self) -> None:
        command = self.command()
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert self._process.stdout is not None
        for line in self._process.stdout:
            line = line.rstrip()
            if line:
                self.progress.emit(line)
            if line == "TRAINING_DONE":
                break
        code = self._process.wait()
        ok = code == 0
        self.finished_training.emit(ok, f"Träning avslutad (kod {code})")

    def cancel(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
