from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xray_detector.dataset.coco import CocoDataset
from xray_detector.util.files import atomic_write_json, read_json

SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def bump_patch(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Ogiltig versionsstrang: {version!r}")
    major, minor, patch = (int(part) for part in parts)
    return f"{major}.{minor}.{patch + 1}"


@dataclass
class DatasetMetadata:
    dataset_id: str
    version: str
    created_at: str
    updated_at: str
    revision: int = 0
    name: str = ""
    source: str = ""
    schema_version: int = SCHEMA_VERSION
    image_count: int = 0
    annotation_count: int = 0
    categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "version": self.version,
            "revision": self.revision,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "schema_version": self.schema_version,
            "image_count": self.image_count,
            "annotation_count": self.annotation_count,
            "categories": self.categories,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetMetadata":
        return cls(
            dataset_id=str(data["dataset_id"]),
            version=str(data.get("version", "1.0.0")),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
            revision=int(data.get("revision", 0)),
            name=str(data.get("name", "")),
            source=str(data.get("source", "")),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            image_count=int(data.get("image_count", 0)),
            annotation_count=int(data.get("annotation_count", 0)),
            categories=[str(item) for item in data.get("categories", [])],
        )

    def refresh(self, dataset: CocoDataset) -> None:
        self.image_count = len(dataset.images)
        self.annotation_count = len(dataset.annotations)
        self.categories = sorted(category.name for category in dataset.categories)
        self.updated_at = utc_now_iso()


def read_metadata(path: Path) -> DatasetMetadata:
    return DatasetMetadata.from_dict(read_json(path))


def write_metadata(metadata: DatasetMetadata, path: Path) -> None:
    atomic_write_json(path, metadata.to_dict())
