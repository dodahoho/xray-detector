"""Registry of base and trained detection models."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from xray_detector.config import AppConfig, load_model_config
from xray_detector.domain.detection import ModelMetadata

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._models: dict[str, ModelMetadata] = {}
        self.refresh()

    def refresh(self) -> None:
        models: dict[str, ModelMetadata] = {}
        model_config = load_model_config()
        for entry in model_config.get("models", []):
            metadata = ModelMetadata(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                family=entry.get("family", "yolo"),
                path=Path(entry.get("path", entry["id"])),
                trained=False,
                manifest={"description": entry.get("description", "")},
            )
            models[metadata.id] = metadata
        models.update(self._scan_trained())
        self._models = models
        logger.info("Model registry loaded %d models", len(self._models))

    def _scan_trained(self) -> dict[str, ModelMetadata]:
        result: dict[str, ModelMetadata] = {}
        if not self.config.models_dir.exists():
            return result
        for manifest_path in sorted(self.config.models_dir.glob("*/*/training_manifest.json")):
            try:
                with manifest_path.open("r", encoding="utf-8") as handle:
                    manifest = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            weights = manifest.get("weights", {}).get("best")
            if not weights:
                for candidate in ("best.pt", "best.pth", "last.pt", "last.pth"):
                    path = manifest_path.parent / candidate
                    if path.exists():
                        weights = str(path)
                        break
            if not weights or not Path(weights).exists():
                continue
            class_names = manifest.get("class_names") or []
            if isinstance(class_names, list):
                classes = {index: str(name) for index, name in enumerate(class_names)}
            else:
                classes = {int(key): str(value) for key, value in class_names.items()}
            version = manifest.get("dataset_version", manifest_path.parent.name)
            run_name = manifest.get("run_name", manifest_path.parent.parent.name)
            model_id = manifest.get("model_id") or f"{run_name}:{version}"
            metadata = ModelMetadata(
                id=model_id,
                name=run_name,
                family=manifest.get("family", "yolo"),
                path=Path(weights),
                classes=classes,
                trained=True,
                manifest=manifest,
            )
            result[metadata.id] = metadata
        return result

    def list_models(self, include_trained: bool = True) -> list[ModelMetadata]:
        models = list(self._models.values())
        if not include_trained:
            models = [model for model in models if not model.trained]
        return sorted(models, key=lambda model: (model.trained, model.name.lower()))

    def get(self, model_id: str) -> ModelMetadata:
        if model_id not in self._models:
            raise KeyError(f"Unknown model: {model_id}")
        return self._models[model_id]

    def default_model(self) -> ModelMetadata:
        model_id = self.config.app.default_model
        if model_id in self._models:
            return self._models[model_id]
        models = self.list_models(include_trained=False)
        if not models:
            raise KeyError("No models configured")
        return models[0]

    def base_models(self) -> list[ModelMetadata]:
        return self.list_models(include_trained=False)
