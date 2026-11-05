"""TrainingWorker – QThread som kör ultralytics-träning.

Kör `model.train(...)` i en separat tråd och emitterar logg/progress via
signals. Vid slutförande sparas vikterna med ett versionsnamn kopplat till
datasetversionen och registreras i models/.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QThread, Signal


class TrainingWorker(QThread):
    """Kör träning i bakgrunden.

    Signals:
        log(str): en logglinje
        progress(float): 0.0–1.0 (fraktion av epochs)
        finished_ok(str): path till sparade vikter
        failed(str): felmeddelande
    """

    log = Signal(str)
    progress = Signal(float)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        base_model_path: str,
        data_yaml: str,
        epochs: int,
        imgsz: int,
        batch: int,
        device: int | str,
        project_dir: Path,
        parent=None,
    ):
        super().__init__(parent)
        self.base_model_path = base_model_path
        self.data_yaml = data_yaml
        self.epochs = epochs
        self.imgsz = imgsz
        self.batch = batch
        self.device = device
        self.project_dir = Path(project_dir)
        self._stop = False

    def _emit(self, msg: str) -> None:
        self.log.emit(msg)
        logger.info("[träning] {}", msg)

    def run(self) -> None:
        try:
            from ultralytics import YOLO
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Ultralytics kunde inte importeras: {e}")
            return

        try:
            self._emit(f"Laddar basmodell: {self.base_model_path}")
            model = YOLO(self.base_model_path)

            # Callback för progress
            def on_fit_epoch_end(trainer):
                epoch = getattr(trainer, "epoch", 0)
                total = getattr(trainer, "epochs", self.epochs) or self.epochs
                frac = (epoch + 1) / max(1, total)
                self.progress.emit(min(1.0, frac))
                self._emit(f"Epoch {epoch + 1}/{total} slutfört")

            def on_train_end(trainer):
                self.progress.emit(1.0)

            model.add_callback("on_fit_epoch_end", on_fit_epoch_end)
            model.add_callback("on_train_end", on_train_end)

            self._emit(
                f"Startar träning: epochs={self.epochs} imgsz={self.imgsz} "
                f"batch={self.batch} device={self.device}"
            )
            model.train(
                data=self.data_yaml,
                epochs=self.epochs,
                imgsz=self.imgsz,
                batch=self.batch,
                device=self.device,
                project=str(self.project_dir),
                name="train",
                exist_ok=True,
                verbose=True,
            )

            # Spara vikter med versionsnamn
            best = self.project_dir / "train" / "weights" / "best.pt"
            if not best.exists():
                # Fallback: senaste
                candidates = sorted(
                    (self.project_dir / "train" / "weights").glob("*.pt"),
                    key=lambda p: p.stat().st_mtime,
                )
                best = candidates[-1] if candidates else None
            if best is None or not best.exists():
                self.failed.emit("Träning slutförde men inga vikter hittades")
                return

            # Namnge efter datasetversion (från data_yaml-path)
            ds_version = self._extract_version(self.data_yaml)
            stamp = datetime.now().strftime("%Y%m%d")
            base_name = Path(self.base_model_path).stem
            out_name = f"{base_name}_{ds_version}_{stamp}.pt"
            out_path = self.project_dir / "train" / "weights" / out_name
            best.rename(out_path)
            self._emit(f"Vikter sparas som: {out_path}")
            self.finished_ok.emit(str(out_path))
        except Exception as e:  # noqa: BLE001
            logger.exception("Träning misslyckades")
            self.failed.emit(str(e))

    def _extract_version(self, data_yaml: str) -> str:
        """Hämta datasetversion ur data_yaml-path (t.ex. .../v3/yolo/data.yaml)."""
        parts = Path(data_yaml).parts
        for p in parts:
            if p.startswith("v") and p[1:].isdigit():
                return p
        return "unknown"

    def stop(self) -> None:
        self._stop = True
