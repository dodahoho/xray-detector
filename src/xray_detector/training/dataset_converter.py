from __future__ import annotations

import random
import shutil
from dataclasses import dataclass
from pathlib import Path

from xray_detector.dataset.coco import CocoDataset
from xray_detector.dataset.store import DatasetStore
from xray_detector.models import Detection
from xray_detector.util.files import atomic_write_text
from xray_detector.util.geometry import detection_to_yolo


@dataclass(frozen=True)
class YoloDatasetInfo:
    data_yaml: Path
    class_names: list[str]
    train_images: int
    val_images: int


def prepare_yolo_dataset(store: DatasetStore, output_dir: Path | str) -> YoloDatasetInfo:
    dataset, _ = store.load()
    if not dataset.images:
        raise ValueError("Datasetet innehaller inga bilder")
    if not dataset.annotations:
        raise ValueError("Datasetet innehaller inga annotationer")

    target = Path(output_dir)
    if target.exists():
        shutil.rmtree(target)
    for split in ("train", "val"):
        (target / "images" / split).mkdir(parents=True, exist_ok=True)
        (target / "labels" / split).mkdir(parents=True, exist_ok=True)

    categories = sorted(dataset.categories, key=lambda item: item.id)
    index_by_category = {category.id: index for index, category in enumerate(categories)}
    images_by_id = {image.id: image for image in dataset.images}
    annotations_by_image: dict[int, list] = {}
    for annotation in dataset.annotations:
        annotations_by_image.setdefault(annotation.image_id, []).append(annotation)

    groups: dict[str, list[int]] = {}
    for image in dataset.images:
        group = image.capture_group or f"image-{image.id}"
        groups.setdefault(group, []).append(image.id)

    group_names = sorted(groups)
    rng = random.Random(42)
    rng.shuffle(group_names)
    if len(group_names) >= 5:
        split_index = max(1, int(len(group_names) * 0.8))
        if split_index >= len(group_names):
            split_index = len(group_names) - 1
        train_groups = set(group_names[:split_index])
        val_groups = set(group_names[split_index:])
    else:
        train_groups = set(group_names)
        val_groups = set(group_names)

    def choose_split(image_id: int) -> str:
        image = images_by_id[image_id]
        group = image.capture_group or f"image-{image.id}"
        return "train" if group in train_groups else "val"

    counters = {"train": 0, "val": 0}
    for image in dataset.images:
        split = choose_split(image.id)
        source = store.image_path(image)
        if not source.exists():
            raise FileNotFoundError(f"Bilden saknas: {source}")
        image_name = f"{image.id}_{Path(image.file_name).name}"
        shutil.copy2(source, target / "images" / split / image_name)
        lines: list[str] = []
        for annotation in annotations_by_image.get(image.id, []):
            class_index = index_by_category[annotation.category_id]
            x, y, w, h = annotation.bbox
            detection = Detection(x, y, x + w, y + h, class_index, "")
            cx, cy, nw, nh = detection_to_yolo(detection, image.width, image.height)
            lines.append(f"{class_index} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
        label_name = f"{Path(image_name).stem}.txt"
        atomic_write_text(
            target / "labels" / split / label_name,
            "\n".join(lines) + ("\n" if lines else ""),
        )
        counters[split] += 1

    names = [category.name for category in categories]
    yaml_lines = [
        f"path: {target.resolve().as_posix()}",
        "train: images/train",
        "val: images/val",
        f"nc: {len(names)}",
        "names:",
    ]
    for index, name in enumerate(names):
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        yaml_lines.append(f'  {index}: "{escaped}"')
    data_yaml = target / "data.yaml"
    atomic_write_text(data_yaml, "\n".join(yaml_lines) + "\n")
    return YoloDatasetInfo(
        data_yaml=data_yaml,
        class_names=names,
        train_images=counters["train"],
        val_images=counters["val"],
    )
