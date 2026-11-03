"""COCO-format: läsa/skriva images, annotations och categories.

En COCO-datasetversion ligger i en mapp:
    <root>/<version>/
        images/          # 000001.jpg, ...
        annotations.json # COCO: images, annotations, categories
        meta.json        # {version, created, num_images, num_objects, ...}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CocoAnnotation:
    """En COCO-annotation (bounding box)."""
    id: int
    image_id: int
    category_id: int
    bbox: list[float]  # [x, y, w, h] (top-left, pixels)
    area: float
    is_ignored: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image_id": self.image_id,
            "category_id": self.category_id,
            "bbox": self.bbox,
            "area": self.area,
            "iscrowd": self.is_ignored,
        }


@dataclass
class CocoImage:
    id: int
    file_name: str
    width: int
    height: int
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_name": self.file_name,
            "width": self.width,
            "height": self.height,
            "path": self.path,
        }


@dataclass
class CocoCategory:
    id: int
    name: str
    supercategory: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "supercategory": self.supercategory,
        }


class CocoDataset:
    """Inminnesrepresentation av en COCO-datasetversion."""

    def __init__(self, root: Path, version: str):
        self.root = Path(root)
        self.version = version
        self.dir = self.root / version
        self.images_dir = self.dir / "images"
        self.annotations_path = self.dir / "annotations.json"
        self.meta_path = self.dir / "meta.json"

        self.images: list[CocoImage] = []
        self.annotations: list[CocoAnnotation] = []
        self.categories: list[CocoCategory] = []
        self.meta: dict[str, Any] = {}

    # ---- Persistens ----
    def ensure_dirs(self) -> None:
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        self.ensure_dirs()
        coco = {
            "images": [i.to_dict() for i in self.images],
            "annotations": [a.to_dict() for a in self.annotations],
            "categories": [c.to_dict() for c in self.categories],
        }
        with open(self.annotations_path, "w", encoding="utf-8") as f:
            json.dump(coco, f, indent=2, ensure_ascii=False)
        self._save_meta()

    def _save_meta(self) -> None:
        self.meta["version"] = self.version
        self.meta["num_images"] = len(self.images)
        self.meta["num_objects"] = len(self.annotations)
        self.meta["num_categories"] = len(self.categories)
        self.meta["categories"] = [c.name for c in self.categories]
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        if not self.annotations_path.exists():
            return
        with open(self.annotations_path, "r", encoding="utf-8") as f:
            coco = json.load(f)
        self.images = [
            CocoImage(
                id=i["id"], file_name=i["file_name"],
                width=i["width"], height=i["height"],
                path=i.get("path", ""),
            )
            for i in coco.get("images", [])
        ]
        self.annotations = [
            CocoAnnotation(
                id=a["id"], image_id=a["image_id"],
                category_id=a["category_id"], bbox=a["bbox"],
                area=a.get("area", 0.0), is_ignored=a.get("iscrowd", 0),
            )
            for a in coco.get("annotations", [])
        ]
        self.categories = [
            CocoCategory(id=c["id"], name=c["name"],
                         supercategory=c.get("supercategory", ""))
            for c in coco.get("categories", [])
        ]
        if self.meta_path.exists():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.meta = json.load(f)

    # ---- ID-hjälpare ----
    @property
    def next_image_id(self) -> int:
        return max((i.id for i in self.images), default=0) + 1

    @property
    def next_annotation_id(self) -> int:
        return max((a.id for a in self.annotations), default=0) + 1

    def category_id_for(self, name: str) -> int:
        """Returnera category_id för ett klassnamn (skapar det om saknas)."""
        for c in self.categories:
            if c.name == name:
                return c.id
        new_id = max((c.id for c in self.categories), default=0) + 1
        self.categories.append(CocoCategory(id=new_id, name=name))
        return new_id

    def add_image(self, file_name: str, width: int, height: int) -> CocoImage:
        img = CocoImage(
            id=self.next_image_id, file_name=file_name,
            width=width, height=height,
        )
        self.images.append(img)
        return img

    def add_annotation(self, image_id: int, category_id: int,
                       x: float, y: float, w: float, h: float) -> CocoAnnotation:
        ann = CocoAnnotation(
            id=self.next_annotation_id,
            image_id=image_id,
            category_id=category_id,
            bbox=[float(x), float(y), float(w), float(h)],
            area=float(w * h),
        )
        self.annotations.append(ann)
        return ann
