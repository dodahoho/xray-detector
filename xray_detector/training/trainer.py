import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal


@dataclass
class TrainConfig:
    dataset_yaml: Path
    weights: str
    output_dir: Path
    epochs: int = 100
    imgsz: int = 640
    batch: int = 16


class TrainingWorker(QThread):
    progress = Signal(str)
    finished_training = Signal(bool, str)

    def __init__(self, config: TrainConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._process: subprocess.Popen | None = None

    def run(self) -> None:
        command = [
            sys.executable,
            "-m",
            "xray_detector.training.train_task",
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
        ]
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
