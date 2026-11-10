import json
from datetime import UTC, datetime
from pathlib import Path

import cv2

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json


class DatasetStore:
    def __init__(self, root: Path, classes: list[str]) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.classes = list(classes)

    def current_version(self) -> int:
        versions = self.versions()
        return max(versions) if versions else 0

    def versions(self) -> list[int]:
        versions = []
        for path in self.root.iterdir():
            if path.is_dir() and path.name.startswith("v"):
                try:
                    versions.append(int(path.name[1:]))
                except ValueError:
                    continue
        return sorted(versions)

    def version_dir(self, version: int) -> Path:
        return self.root / f"v{version}"

    def _ensure_version(self, version: int) -> Path:
        path = self.version_dir(version)
        (path / "images").mkdir(parents=True, exist_ok=True)
        return path

    def _load_coco(self, version: int) -> dict:
        path = self.version_dir(version) / "dataset.json"
        if path.exists():
            with open(path, encoding="utf-8") as file:
                return json.load(file)
        now = datetime.now(UTC).isoformat()
        return {
            "info": {
                "version": version,
                "created": now,
                "updated": now,
                "num_images": 0,
                "num_objects": 0,
            },
            "categories": [
                {"id": i, "name": name} for i, name in enumerate(self.classes)
            ],
            "images": [],
            "annotations": [],
        }

    def _save_coco(self, version: int, coco: dict) -> None:
        coco["info"]["updated"] = datetime.now(UTC).isoformat()
        coco["info"]["num_images"] = len(coco["images"])
        coco["info"]["num_objects"] = len(coco["annotations"])
        atomic_write_json(self.version_dir(version) / "dataset.json", coco)

    def _category_id(self, coco: dict, class_name: str) -> int:
        for category in coco["categories"]:
            if category["name"] == class_name:
                return category["id"]
        new_id = len(coco["categories"])
        coco["categories"].append({"id": new_id, "name": class_name})
        self.classes.append(class_name)
        return new_id

    def add_samples(
        self,
        version: int,
        samples: list[AnnotatedImage],
        captured: str | None = None,
    ) -> None:
        path = self._ensure_version(version)
        coco = self._load_coco(version)
        image_id = max((img["id"] for img in coco["images"]), default=0) + 1
        annotation_id = max((ann["id"] for ann in coco["annotations"]), default=0) + 1
        group_id = max((img.get("group", 0) for img in coco["images"]), default=0) + 1
        stamp = captured or datetime.now(UTC).isoformat()
        for sample in samples:
            image_name = f"img_{image_id:06d}.png"
            cv2.imwrite(str(path / "images" / image_name), sample.frame)
            height, width = sample.frame.shape[:2]
            coco["images"].append(
                {
                    "id": image_id,
                    "file_name": image_name,
                    "width": width,
                    "height": height,
                    "group": group_id,
                    "captured": stamp,
                }
            )
            for annotation in sample.annotations:
                category_id = self._category_id(coco, annotation["class_name"])
                x, y, w, h = annotation["bbox"]
                coco["annotations"].append(
                    {
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": category_id,
                        "bbox": [x, y, w, h],
                    }
                )
                annotation_id += 1
            image_id += 1
        self._save_coco(version, coco)

    def metadata(self, version: int) -> dict:
        return self._load_coco(version)["info"]

    def delete_images(self, version: int, image_ids: list[int]) -> None:
        coco = self._load_coco(version)
        ids = set(image_ids)
        file_names = {
            img["file_name"] for img in coco["images"] if img["id"] in ids
        }
        coco["images"] = [img for img in coco["images"] if img["id"] not in ids]
        coco["annotations"] = [
            ann for ann in coco["annotations"] if ann["image_id"] not in ids
        ]
        self._save_coco(version, coco)
        for name in file_names:
            (self.version_dir(version) / "images" / name).unlink(missing_ok=True)

    def load_coco(self, version: int) -> dict:
        return self._load_coco(version)

    def new_version(self) -> int:
        return self.current_version() + 1
