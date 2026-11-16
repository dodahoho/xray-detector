from pathlib import Path

from xray_detector.domain.dataset import AnnotatedImage, VariationSettings
from xray_detector.infrastructure.dataset_store.export import (
    SPLIT_RATIO,
    SPLIT_SEED,
    export_coco,
    export_rfdetr,
    export_yolo,
    group_count,
    train_val_split,
    train_val_test_split,
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
    """Fasad över datasetlagringen: sparade bilder, klasser och exporter."""

    def __init__(self, root: Path) -> None:
        self.store = DatasetStore(root)
        self.data_dir = Path(root).parent

    @property
    def images_dir(self) -> Path:
        return self.store.images_dir

    def classes(self) -> list[str]:
        """Datasetets klasser; datasetet är master för klasslistan (TASK-61)."""
        return self.store.classes()

    def has_dataset(self) -> bool:
        return self.store.has_dataset()

    def set_classes(self, names: list[str]) -> None:
        self.store.set_classes(names)

    def class_in_use(self, name: str) -> bool:
        return self.store.class_in_use(name)

    def add_samples(
        self,
        samples: list[AnnotatedImage],
        captured: str | None = None,
    ) -> None:
        self.store.add_samples(samples, captured)

    def delete_images(self, image_ids: list[int]) -> None:
        self.store.delete_images(image_ids)

    def add_variations(
        self,
        settings: VariationSettings,
        seed: int | None = None,
    ) -> int:
        """Utökar datasetet med syntetiska variationer; antalet tillagda bildpar (TASK-88)."""
        return self.store.add_variations(settings, seed)

    def delete_synthetic(self) -> int:
        """Raderar alla syntetiska bilder; antalet borttagna bilder (TASK-88)."""
        return self.store.delete_synthetic()

    def load_dataset(self) -> dict:
        """Datasetet som läsmodell: klasser och bilder med annoteringar i pixlar."""
        return self.store.load_dataset()

    def metadata(self) -> dict:
        return self.store.metadata()

    def image_sizes(self) -> list[tuple[int, int, int]]:
        """Datasetets upplösningar som (bredd, höjd, antal), vanligaste först (TASK-80)."""
        return self.store.image_sizes()

    def image_pair_count(self) -> int:
        """Antal bildpar (fångstgrupper) i datasetet (TASK-73, TASK-101)."""
        return group_count(self.load_dataset()["images"])

    def export_yolo(self, export_root: Path, ratio: float = SPLIT_RATIO) -> Path:
        return export_yolo(self.store, export_root, ratio)

    def export_coco(self, export_root: Path) -> Path:
        return export_coco(self.store, export_root)

    def export_rfdetr(
        self,
        export_root: Path,
        ratio: float = SPLIT_RATIO,
        seed: int = SPLIT_SEED,
    ) -> Path:
        return export_rfdetr(self.store, export_root, ratio, seed)

    def train_val_counts(
        self,
        ratio: float = SPLIT_RATIO,
        seed: int = SPLIT_SEED,
        family: str = "yolo",
    ) -> tuple[int, int]:
        """Antal bildpar i train respektive val för den seedade grupp-delningen (TASK-72).

        RF-DETR:s export har också en test-del, så val blir mindre där (TASK-93).
        """
        images = self.load_dataset()["images"]
        if family == "rfdetr":
            splits = train_val_test_split(images, ratio, seed)
            return group_count(splits["train"]), group_count(splits["valid"])
        train, val = train_val_split(images, ratio, seed)
        return group_count(train), group_count(val)


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
