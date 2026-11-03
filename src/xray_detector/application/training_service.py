"""Training orchestration using an isolated worker process."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from xray_detector.application.dataset_service import DatasetService
from xray_detector.config import AppConfig
from xray_detector.domain.training import TrainingRequest


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned or "run"


class TrainingService(QObject):
    log = Signal(str)
    finished = Signal(bool, str, object)

    def __init__(self, config: AppConfig, dataset_service: DatasetService) -> None:
        super().__init__()
        self.config = config
        self.dataset_service = dataset_service
        self._process: QProcess | None = None
        self._request: TrainingRequest | None = None
        self._run_dir: Path | None = None
        self._model_dir: Path | None = None
        self._export_manifest: dict = {}
        self._log_path: Path | None = None
        self._stopping = False

    @property
    def is_running(self) -> bool:
        return (
            self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning
        )

    def start(self, request: TrainingRequest) -> tuple[bool, str]:
        if self.is_running:
            return False, "Training is already running"
        self._stopping = False

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        run_name = _safe_name(request.run_name or "run")
        self._run_dir = self.config.runs_dir / f"{run_name}_{timestamp}"
        self._model_dir = (
            self.config.models_dir / run_name / f"{request.dataset_version}_{timestamp}"
        )
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._model_dir.mkdir(parents=True, exist_ok=True)

        family = request.family.lower()
        export_root = self._run_dir / ("dataset_coco" if family == "rfdetr" else "dataset_yolo")
        try:
            primary, data_dir, export_manifest = self.dataset_service.export_for_training(
                request.dataset_name,
                request.dataset_version,
                export_root,
                family,
            )
        except Exception as exc:
            return False, f"Dataset export failed: {exc}"

        self._export_manifest = export_manifest
        self._request = request

        worker_config = {
            "family": family,
            "base_model_id": request.base_model_id,
            "base_model_path": request.base_model_path,
            "variant": request.base_model_id,
            "data_yaml": str(primary) if family == "yolo" else None,
            "data_dir": str(data_dir),
            "run_dir": str(self._run_dir),
            "model_dir": str(self._model_dir),
            "dataset_name": request.dataset_name,
            "dataset_version": request.dataset_version,
            "params": asdict(request.params),
        }
        config_path = self._run_dir / "training_config.json"
        with config_path.open("w", encoding="utf-8") as handle:
            json.dump(worker_config, handle, indent=2, ensure_ascii=False)

        self._log_path = self._run_dir / "training.log"
        self._log_path.write_text("", encoding="utf-8")

        process = QProcess(self)
        process.setWorkingDirectory(str(self._run_dir))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        process.setProcessEnvironment(env)
        process.readyReadStandardOutput.connect(self._drain_output)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error)
        self._process = process

        self.log.emit(
            f"Starting training ({family}) for dataset {request.dataset_name} {request.dataset_version}"
        )
        self.log.emit(f"Run directory: {self._run_dir}")
        self.log.emit(f"Model directory: {self._model_dir}")
        process.start(
            sys.executable,
            ["-m", "xray_detector.infrastructure.training.worker", str(config_path)],
        )
        if not process.waitForStarted(5000):
            message = f"Could not start training process: {process.errorString()}"
            self.log.emit(message)
            process.deleteLater()
            self._process = None
            return False, message
        return True, "Training started"

    def stop(self) -> None:
        if self._process is None:
            return
        self._stopping = True
        self.log.emit("Stopping training...")
        self._process.terminate()
        if not self._process.waitForFinished(5000):
            self._process.kill()
            self._process.waitForFinished(3000)

    def _drain_output(self) -> None:
        if self._process is None:
            return
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if not data:
            return
        self.log.emit(data.rstrip())
        if self._log_path is not None:
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(data)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.log.emit(
                f"Training process failed to start: {self._process.errorString() if self._process else ''}"
            )

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        process = self._process
        self._process = None
        if process is not None:
            process.deleteLater()
        if self._log_path is not None and self._log_path.exists():
            self.log.emit(f"Training log: {self._log_path}")

        if exit_code != 0:
            if self._stopping:
                message = "Training stopped by user"
            else:
                message = f"Training failed (exit code {exit_code})"
                if exit_status == QProcess.ExitStatus.CrashExit:
                    message = "Training process crashed"
            self._stopping = False
            self.log.emit(message)
            self.finished.emit(False, message, {"run_dir": str(self._run_dir)})
            return

        if self._model_dir is None or self._request is None or self._run_dir is None:
            self.finished.emit(False, "Training finished without output metadata", {})
            return

        weights = self._find_weights(self._model_dir)
        if not weights:
            message = f"Training finished but no weights were found in {self._model_dir}"
            self.log.emit(message)
            self.finished.emit(False, message, {"run_dir": str(self._run_dir)})
            return

        manifest = self._write_manifest(weights)
        self._stopping = False
        message = f"Training complete. Model saved as {manifest['model_id']}"
        self.log.emit(message)
        self.finished.emit(True, message, manifest)

    def _find_weights(self, model_dir: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in ("best.pt", "best.pth", "last.pt", "last.pth"):
            path = model_dir / name
            if path.exists():
                key = "best" if name.startswith("best") else "last"
                result.setdefault(key, str(path))
        if "best" not in result and result:
            result["best"] = next(iter(result.values()))
        if result and "last" not in result:
            result["last"] = result["best"]
        return result

    def _write_manifest(self, weights: dict[str, str]) -> dict:
        assert self._request is not None
        assert self._model_dir is not None
        assert self._run_dir is not None

        metrics = {}
        metrics_path = self._model_dir / "metrics.json"
        if metrics_path.exists():
            try:
                with metrics_path.open("r", encoding="utf-8") as handle:
                    metrics = json.load(handle)
            except (OSError, json.JSONDecodeError):
                metrics = {}

        class_names = self._export_manifest.get("class_names")
        if class_names is None:
            class_names = sorted(self._export_manifest.get("category_counts", {}).keys())

        manifest = {
            "model_id": f"{self._request.run_name}:{self._model_dir.name}",
            "run_name": self._request.run_name,
            "family": self._request.family,
            "dataset": self._request.dataset_name,
            "dataset_version": self._request.dataset_version,
            "base_model": self._request.base_model_id,
            "base_model_path": self._request.base_model_path,
            "created_at": _utc_now(),
            "params": asdict(self._request.params),
            "class_names": class_names,
            "weights": weights,
            "metrics": metrics,
            "run_dir": str(self._run_dir),
            "training_log": str(self._log_path) if self._log_path else None,
        }
        path = self._model_dir / "training_manifest.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
        return manifest
