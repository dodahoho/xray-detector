from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from src.core.models_schema import TrainedModelInfo
from src.ml.base import BaseDetector, BaseTrainer, SimulatedXrayDetector
from src.ml.rfdetr_backend import RfDetrDetector, RfDetrTrainer
from src.ml.yolo_backend import YoloDetector, YoloTrainer


class ModelRegistry:
    """Hanterar tillgängliga basmodeller samt färdigtränade modeller med versionssiffror."""

    def __init__(
        self,
        models_dir: str | Path = "models/trained",
        base_models: List[Dict[str, str]] | None = None,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.base_models = base_models or [
            {"name": "YOLO26-nano (Basmodell)", "family": "YOLO26", "weights": "yolo26n.pt"},
            {"name": "YOLO26-small (Basmodell)", "family": "YOLO26", "weights": "yolo26s.pt"},
            {"name": "YOLO11-nano (Basmodell)", "family": "YOLO", "weights": "yolo11n.pt"},
            {"name": "RF-DETR-base (Basmodell)", "family": "RF-DETR", "weights": "rf-detr-base.pth"},
            {"name": "Simulated X-ray Detector (Snabbtest/Fallback)", "family": "SIMULATED", "weights": "simulated"},
        ]

    def list_trained_models(self) -> List[TrainedModelInfo]:
        """Listar alla tränade modeller från disk (med samma versionssiffra som datasetet de tränats på)."""
        trained: List[TrainedModelInfo] = []
        if not self.models_dir.exists():
            return trained

        for child in self.models_dir.iterdir():
            if not child.is_dir():
                continue
            meta_file = child / "model_meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    trained.append(
                        TrainedModelInfo(
                            version=int(m["version"]),
                            model_family=str(m["model_family"]),
                            base_model_name=str(m.get("base_model_name", m["model_family"])),
                            dataset_version=int(m.get("dataset_version", m["version"])),
                            trained_at=str(m.get("trained_at", "")),
                            weights_path=str(m["weights_path"]),
                            epochs=int(m.get("epochs", 0)),
                            metrics=dict(m.get("metrics", {})),
                        )
                    )
                except Exception:
                    continue

        trained.sort(key=lambda t: (t.version, t.trained_at), reverse=True)
        return trained

    def list_all_selectable_detectors(self) -> List[Dict[str, str]]:
        """Returnerar en samlad lista med både egentränade modellversioner och basmodeller för GUI."""
        items: List[Dict[str, str]] = []
        for tm in self.list_trained_models():
            items.append(
                {
                    "label": f"[Tränad v{tm.version}] {tm.model_family} (Dataset v{tm.dataset_version} – {tm.trained_at})",
                    "family": tm.model_family,
                    "weights": tm.weights_path,
                    "version": str(tm.version),
                }
            )
        for bm in self.base_models:
            items.append(
                {
                    "label": f"[Bas] {bm['name']}",
                    "family": bm["family"],
                    "weights": bm["weights"],
                    "version": "base",
                }
            )
        return items

    @staticmethod
    def create_detector(
        model_family: str,
        weights_path: str = "",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> BaseDetector:
        fam = model_family.upper()
        if "RF-DETR" in fam or "RFDETR" in fam:
            return RfDetrDetector(
                model_family=model_family,
                weights_path=weights_path,
                confidence_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
            )
        if "SIMULATED" in fam:
            return SimulatedXrayDetector(
                model_family=model_family,
                weights_path=weights_path,
                confidence_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
            )
        return YoloDetector(
            model_family=model_family,
            weights_path=weights_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
        )

    @staticmethod
    def create_trainer(model_family: str) -> BaseTrainer:
        fam = model_family.upper()
        if "RF-DETR" in fam or "RFDETR" in fam:
            return RfDetrTrainer()
        return YoloTrainer()
