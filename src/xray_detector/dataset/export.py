from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xray_detector.dataset.coco import Annotation, CocoDataset, ImageRecord, write_coco
from xray_detector.dataset.store import DatasetStore
from xray_detector.dataset.versioning import (
    DatasetMetadata,
    bump_patch,
    utc_now_iso,
)
from xray_detector.models import Detection
from xray_detector.util.files import atomic_write_json, atomic_write_text, sha256_file
from xray_detector.util.geometry import detection_to_yolo

VALID_FORMATS = {"coco", "yolo"}


@dataclass
class ExportResult:
    directory: Path
    manifest: dict[str, Any]
    archive: Path | None = None


def export_dataset(
    store: DatasetStore,
    export_root: Path | str,
    formats: tuple[str, ...] | list[str] = ("coco", "yolo"),
    freeze_version: bool = True,
    create_archive: bool = False,
) -> ExportResult:
    selected = tuple(dict.fromkeys(formats))
    invalid = set(selected) - VALID_FORMATS
    if invalid:
        raise ValueError(f"Okanda exportformat: {sorted(invalid)}")
    if not selected:
        raise ValueError("Minst ett exportformat kravs")

    dataset, metadata = store.load()
    version = bump_patch(metadata.version) if freeze_version else metadata.version
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = Path(export_root) / f"{store.dataset_id}-v{version}-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    images_dir = target / "images"
    images_dir.mkdir()

    try:
        image_names: dict[int, str] = {}
        for record in dataset.images:
            source = store.image_path(record)
            if not source.exists():
                raise FileNotFoundError(f"Bilden saknas: {source}")
            name = Path(record.file_name).name
            if name in image_names.values():
                raise ValueError(f"Dubblerat bildfilnamn vid export: {name}")
            shutil.copy2(source, images_dir / name)
            image_names[record.id] = name

        if "coco" in selected:
            exported = CocoDataset(
                images=[
                    ImageRecord(
                        id=record.id,
                        file_name=f"images/{image_names[record.id]}",
                        width=record.width,
                        height=record.height,
                        capture_group=record.capture_group,
                        camera=record.camera,
                    )
                    for record in dataset.images
                ],
                annotations=list(dataset.annotations),
                categories=list(dataset.categories),
            )
            write_coco(exported, target / "annotations.json")

        if "yolo" in selected:
            _write_yolo(dataset, image_names, target)

        manifest: dict[str, Any] = {
            "dataset_id": store.dataset_id,
            "dataset_name": metadata.name,
            "version": version,
            "revision": metadata.revision,
            "created_at": metadata.created_at,
            "updated_at": metadata.updated_at,
            "exported_at": utc_now_iso(),
            "image_count": len(dataset.images),
            "annotation_count": len(dataset.annotations),
            "object_count": len(dataset.annotations),
            "category_count": len(dataset.categories),
            "categories": sorted(category.name for category in dataset.categories),
            "formats": list(selected),
            "source": metadata.source,
        }
        if "coco" in selected:
            manifest["annotations_sha256"] = sha256_file(target / "annotations.json")
        atomic_write_json(target / "manifest.json", manifest)

        if freeze_version:
            metadata.version = version
            metadata.revision = 0
            store.save(dataset, metadata)
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise

    archive = None
    if create_archive:
        archive = Path(
            shutil.make_archive(str(target), "zip", root_dir=target.parent, base_dir=target.name)
        )
    return ExportResult(directory=target, manifest=manifest, archive=archive)


def _write_yolo(
    dataset: CocoDataset,
    image_names: dict[int, str],
    target: Path,
) -> None:
    labels_dir = target / "labels"
    labels_dir.mkdir(exist_ok=True)
    categories = sorted(dataset.categories, key=lambda item: item.id)
    index_by_category = {category.id: index for index, category in enumerate(categories)}
    images_by_id = {image.id: image for image in dataset.images}

    by_image: dict[int, list[Annotation]] = {}
    for annotation in dataset.annotations:
        by_image.setdefault(annotation.image_id, []).append(annotation)

    for image_id, name in image_names.items():
        record = images_by_id[image_id]
        lines: list[str] = []
        for annotation in by_image.get(image_id, []):
            class_index = index_by_category[annotation.category_id]
            x, y, w, h = annotation.bbox
            detection = Detection(x, y, x + w, y + h, class_index, "")
            cx, cy, nw, nh = detection_to_yolo(detection, record.width, record.height)
            lines.append(f"{class_index} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
        atomic_write_text(labels_dir / f"{Path(name).stem}.txt", "\n".join(lines) + ("\n" if lines else ""))

    names = {index: category.name for index, category in enumerate(categories)}
    yaml_lines = [
        "path: .",
        "train: images",
        "val: images",
        f"nc: {len(categories)}",
        "names:",
    ]
    for index, name in names.items():
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        yaml_lines.append(f'  {index}: "{escaped}"')
    atomic_write_text(target / "data.yaml", "\n".join(yaml_lines) + "\n")
