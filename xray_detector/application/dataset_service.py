from pathlib import Path

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.export import (
    SPLIT_RATIO,
    SPLIT_SEED,
    export_coco,
    export_yolo,
    train_val_split,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore


class DatasetService:
    """Fasad över datasetlagringen: versioner, sparade bilder och exporter."""

    def __init__(self, root: Path, classes: list[str]) -> None:
        self.store = DatasetStore(root, classes)

    def versions(self) -> list[int]:
        return self.store.versions()

    def current_version(self) -> int:
        return self.store.current_version()

    def new_version(self) -> int:
        return self.store.new_version()

    def add_samples(self, version: int, samples: list[AnnotatedImage]) -> None:
        self.store.add_samples(version, samples)

    def delete_images(self, version: int, image_ids: list[int]) -> None:
        self.store.delete_images(version, image_ids)

    def load_coco(self, version: int) -> dict:
        return self.store.load_coco(version)

    def metadata(self, version: int) -> dict:
        return self.store.metadata(version)

    def version_dir(self, version: int) -> Path:
        return self.store.version_dir(version)

    def export_yolo(self, version: int, export_root: Path) -> Path:
        return export_yolo(self.store, version, export_root)

    def export_coco(self, version: int, export_root: Path) -> Path:
        return export_coco(self.store, version, export_root)

    def train_val_counts(self, version: int, ratio: float = SPLIT_RATIO, seed: int = SPLIT_SEED) -> tuple[int, int]:
        """Antal bilder i train respektive val för den seedade grupp-delningen."""
        train, val = train_val_split(self.load_coco(version), ratio, seed)
        return len(train), len(val)
