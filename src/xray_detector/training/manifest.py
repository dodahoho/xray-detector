from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xray_detector.util.files import atomic_write_json, read_json


@dataclass
class ModelMetadata:
    model_id: str
    base_model: str
    dataset_id: str
    dataset_version: str
    dataset_revision: int
    created_at: str
    weights: str = "best.pt"
    parameters: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    class_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "base_model": self.base_model,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "dataset_revision": self.dataset_revision,
            "created_at": self.created_at,
            "weights": self.weights,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "class_names": self.class_names,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelMetadata":
        return cls(
            model_id=str(data["model_id"]),
            base_model=str(data["base_model"]),
            dataset_id=str(data["dataset_id"]),
            dataset_version=str(data["dataset_version"]),
            dataset_revision=int(data.get("dataset_revision", 0)),
            created_at=str(data["created_at"]),
            weights=str(data.get("weights", "best.pt")),
            parameters=dict(data.get("parameters", {})),
            metrics=dict(data.get("metrics", {})),
            class_names=[str(item) for item in data.get("class_names", [])],
        )


def write_model_metadata(metadata: ModelMetadata, path: Path) -> None:
    atomic_write_json(path, metadata.to_dict())


def read_model_metadata(path: Path) -> ModelMetadata:
    return ModelMetadata.from_dict(read_json(path))
