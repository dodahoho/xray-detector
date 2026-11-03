"""Application service for dataset operations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from xray_detector.config import AppConfig
from xray_detector.domain.annotation import AnnotationBox
from xray_detector.domain.dataset import DatasetInfo, DatasetVersionSummary
from xray_detector.infrastructure.dataset_store.coco_export import export_coco
from xray_detector.infrastructure.dataset_store.coco_store import CocoStore, discover_datasets
from xray_detector.infrastructure.dataset_store.rfdetr_export import export_rfdetr
from xray_detector.infrastructure.dataset_store.yolo_export import export_yolo


class DatasetService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        config.ensure_dirs()

    def store(self, name: str | None = None) -> CocoStore:
        dataset_name = name or self.config.app.dataset
        store = CocoStore(self.config.datasets_dir / dataset_name, dataset_name)
        store.ensure()
        return store

    def list_datasets(self) -> list[str]:
        return [store.name for store in discover_datasets(self.config.datasets_dir)]

    def list_versions(self, name: str | None = None) -> list[DatasetVersionSummary]:
        return self.store(name).list_versions()

    def latest_version(self, name: str | None = None) -> str | None:
        return self.store(name).info().latest_version

    def version_summary(self, version: str, name: str | None = None) -> DatasetVersionSummary:
        for summary in self.list_versions(name):
            if summary.version == version:
                return summary
        raise FileNotFoundError(
            f"Version {version} not found in dataset {name or self.config.app.dataset}"
        )

    def category_names(self, name: str | None = None) -> list[str]:
        return self.store(name).category_names()

    def dataset_info(self, name: str | None = None) -> DatasetInfo:
        return self.store(name).info()

    def add_pair(
        self,
        frames: dict[str, np.ndarray],
        annotations: dict[str, list[AnnotationBox]],
        source: dict | None = None,
        name: str | None = None,
        pair_id: str | None = None,
    ) -> DatasetVersionSummary:
        store = self.store(name)
        return store.add_pair(
            frames=frames,
            annotations=annotations,
            source=source,
            jpeg_quality=self.config.dataset.jpeg_quality,
            pair_id=pair_id,
            min_box_size=self.config.dataset.min_box_size,
        )

    def export(
        self,
        version: str,
        fmt: str,
        destination: Path,
        name: str | None = None,
        train_split: float | None = None,
        val_split: float | None = None,
        seed: int | None = None,
    ) -> dict:
        store = self.store(name)
        fmt = fmt.lower()
        if fmt == "coco":
            return export_coco(store, version, destination)
        if fmt == "yolo":
            return export_yolo(
                store,
                version,
                destination,
                train_split=self.config.dataset.train_split if train_split is None else train_split,
                val_split=self.config.dataset.val_split if val_split is None else val_split,
                seed=self.config.dataset.split_seed if seed is None else seed,
            )
        raise ValueError(f"Unknown export format: {fmt}")

    def export_both(
        self,
        version: str,
        destination: Path,
        name: str | None = None,
    ) -> dict[str, dict]:
        dataset_name = name or self.config.app.dataset
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        base = destination / f"{dataset_name}_{version}_{timestamp}"
        return {
            "coco": self.export(version, "coco", base / "coco", dataset_name),
            "yolo": self.export(version, "yolo", base / "yolo", dataset_name),
        }

    def export_for_training(
        self,
        dataset_name: str,
        version: str,
        destination: Path,
        family: str,
    ) -> tuple[Path, Path, dict]:
        """Export a version in the format required by the model family.

        Returns (primary_path, export_directory, export_manifest).
        """
        store = self.store(dataset_name)
        destination.mkdir(parents=True, exist_ok=True)
        if family.lower() == "rfdetr":
            manifest = export_rfdetr(
                store,
                version,
                destination,
                train_split=self.config.dataset.train_split,
                val_split=self.config.dataset.val_split,
                seed=self.config.dataset.split_seed,
            )
            return destination, destination, manifest
        manifest = export_yolo(
            store,
            version,
            destination,
            train_split=self.config.dataset.train_split,
            val_split=self.config.dataset.val_split,
            seed=self.config.dataset.split_seed,
        )
        return destination / "data.yaml", destination, manifest
