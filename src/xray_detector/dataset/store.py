from __future__ import annotations

import re
import shutil
from pathlib import Path

from xray_detector.dataset.coco import (
    Annotation,
    CocoDataset,
    ImageRecord,
    read_coco,
    write_coco,
)
from xray_detector.dataset.pending import PendingCapture
from xray_detector.dataset.versioning import (
    DatasetMetadata,
    bump_patch,
    read_metadata,
    utc_now_iso,
    write_metadata,
)
from xray_detector.models import Detection
from xray_detector.util.geometry import detection_to_coco

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


class DatasetStore:
    """Ett dataset pa disk med COCO-annotationer och metadata."""

    def __init__(self, datasets_root: Path | str, dataset_id: str) -> None:
        if (
            not dataset_id
            or dataset_id in {".", ".."}
            or _SAFE_NAME.search(dataset_id)
        ):
            raise ValueError(f"Ogiltigt dataset-id: {dataset_id!r}")
        self.datasets_root = Path(datasets_root)
        self.dataset_id = dataset_id
        self.root = self.datasets_root / dataset_id
        self.images_dir = self.root / "images"
        self.coco_path = self.root / "annotations.json"
        self.metadata_path = self.root / "metadata.json"

    @property
    def exists(self) -> bool:
        return self.coco_path.exists() and self.metadata_path.exists()

    def create(
        self,
        name: str | None = None,
        source: str = "",
        version: str = "1.0.0",
    ) -> DatasetMetadata:
        if self.exists:
            raise FileExistsError(f"Datasetet {self.dataset_id} finns redan")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        now = utc_now_iso()
        dataset = CocoDataset()
        metadata = DatasetMetadata(
            dataset_id=self.dataset_id,
            name=name or self.dataset_id,
            version=version,
            created_at=now,
            updated_at=now,
            source=source,
        )
        write_coco(dataset, self.coco_path)
        write_metadata(metadata, self.metadata_path)
        return metadata

    def ensure_exists(self, name: str | None = None, source: str = "") -> DatasetMetadata:
        if not self.exists:
            return self.create(name=name, source=source)
        return read_metadata(self.metadata_path)

    def load(self) -> tuple[CocoDataset, DatasetMetadata]:
        if not self.exists:
            raise FileNotFoundError(f"Datasetet {self.dataset_id} finns inte i {self.root}")
        return read_coco(self.coco_path), read_metadata(self.metadata_path)

    def save(self, dataset: CocoDataset, metadata: DatasetMetadata | None = None) -> DatasetMetadata:
        self.images_dir.mkdir(parents=True, exist_ok=True)
        metadata = metadata or read_metadata(self.metadata_path)
        metadata.dataset_id = self.dataset_id
        metadata.refresh(dataset)
        write_coco(dataset, self.coco_path)
        write_metadata(metadata, self.metadata_path)
        return metadata

    def freeze_version(self) -> DatasetMetadata:
        dataset, metadata = self.load()
        metadata.version = bump_patch(metadata.version)
        metadata.revision = 0
        metadata.refresh(dataset)
        write_metadata(metadata, self.metadata_path)
        return metadata

    def image_path(self, record: ImageRecord) -> Path:
        return self.root / record.file_name

    def add_capture(
        self,
        capture: PendingCapture,
        annotations: dict[str, list[Detection]],
    ) -> tuple[int, int]:
        """Lagg till ett capture-par i datasetet. Returnerar (bilder, annotationer)."""
        dataset, metadata = self.load()
        unknown = set(annotations) - set(capture.images)
        if unknown:
            raise ValueError(f"Annotationer for okanda kameror: {sorted(unknown)}")

        group = _SAFE_NAME.sub("_", capture.group_id)
        copied: list[Path] = []
        image_ids: dict[str, int] = {}
        try:
            for camera, pending_image in capture.images.items():
                source = capture.image_path(camera)
                target_name = f"{group}_{camera}{source.suffix.lower()}"
                target = self.images_dir / target_name
                if target.exists():
                    raise FileExistsError(f"Bilden {target_name} finns redan")
                shutil.copy2(source, target)
                copied.append(target)
                image_id = dataset.next_image_id()
                image_ids[camera] = image_id
                dataset.images.append(
                    ImageRecord(
                        id=image_id,
                        file_name=f"images/{target_name}",
                        width=pending_image.width,
                        height=pending_image.height,
                        capture_group=capture.group_id,
                        camera=camera,
                    )
                )

            annotation_count = 0
            for camera, detections in annotations.items():
                image_id = image_ids[camera]
                record = next(image for image in dataset.images if image.id == image_id)
                for detection in detections:
                    category = dataset.ensure_category(detection.class_name)
                    clamped = detection.clamped(record.width, record.height)
                    if clamped.x2 - clamped.x1 < 1 or clamped.y2 - clamped.y1 < 1:
                        continue
                    bbox, area = detection_to_coco(clamped, record.width, record.height)
                    dataset.annotations.append(
                        Annotation(
                            id=dataset.next_annotation_id(),
                            image_id=image_id,
                            category_id=category.id,
                            bbox=bbox,
                            area=area,
                        )
                    )
                    annotation_count += 1

            metadata.revision += 1
            self.save(dataset, metadata)
            return len(copied), annotation_count
        except BaseException:
            for path in copied:
                path.unlink(missing_ok=True)
            raise


def list_dataset_metadata(datasets_root: Path | str) -> list[DatasetMetadata]:
    root = Path(datasets_root)
    if not root.exists():
        return []
    result: list[DatasetMetadata] = []
    for path in sorted(root.iterdir()):
        metadata_path = path / "metadata.json"
        if path.is_dir() and metadata_path.exists():
            try:
                result.append(read_metadata(metadata_path))
            except (OSError, ValueError):
                continue
    return result


def get_or_create_store(
    datasets_root: Path | str,
    dataset_id: str,
    name: str | None = None,
) -> DatasetStore:
    store = DatasetStore(datasets_root, dataset_id)
    store.ensure_exists(name=name)
    return store
