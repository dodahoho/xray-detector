from pathlib import Path

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.export import (
    SPLIT_RATIO,
    SPLIT_SEED,
    export_coco,
    export_rfdetr,
    export_yolo,
    train_val_split,
)
from xray_detector.infrastructure.dataset_store.pending import (
    PendingCapture,
    list_pending,
    pending_saved_at,
    remove_pending,
    save_pending,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore


class DatasetService:
    """Fasad över datasetlagringen: versioner, sparade bilder och exporter."""

    def __init__(self, root: Path, classes: list[str]) -> None:
        self.store = DatasetStore(root, classes)
        self.data_dir = Path(root).parent

    def versions(self) -> list[int]:
        return self.store.versions()

    def current_version(self) -> int:
        return self.store.current_version()

    def new_version(self) -> int:
        return self.store.new_version()

    def add_samples(
        self,
        version: int,
        samples: list[AnnotatedImage],
        captured: str | None = None,
    ) -> None:
        self.store.add_samples(version, samples, captured)

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

    def export_rfdetr(self, version: int, export_root: Path) -> Path:
        return export_rfdetr(self.store, version, export_root)

    def train_val_counts(self, version: int, ratio: float = SPLIT_RATIO, seed: int = SPLIT_SEED) -> tuple[int, int]:
        """Antal bilder i train respektive val för den seedade grupp-delningen."""
        train, val = train_val_split(self.load_coco(version), ratio, seed)
        return len(train), len(val)


    # --- Pending-kn (TASK-12) ---

    def pending_captures(self) -> list[PendingCapture]:
        return list_pending(self.data_dir)

    def save_pending(self, frames) -> str:
        return save_pending(self.data_dir, frames)

    def remove_pending(self, group_id: str) -> None:
        remove_pending(self.data_dir, group_id)

    def pending_saved_at(self, group_id: str) -> str:
        """Tidpunkten då en osparad fångst skrevs (ISO-lik lokal tid)."""
        return pending_saved_at(self.data_dir, group_id)
