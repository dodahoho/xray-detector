from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xray_detector.util.files import atomic_write_json, read_json


@dataclass
class Category:
    id: int
    name: str
    supercategory: str = "object"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "supercategory": self.supercategory}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            supercategory=str(data.get("supercategory", "object")),
        )


@dataclass
class ImageRecord:
    id: int
    file_name: str
    width: int
    height: int
    capture_group: str | None = None
    camera: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "file_name": self.file_name,
            "width": self.width,
            "height": self.height,
        }
        if self.capture_group is not None:
            data["capture_group"] = self.capture_group
        if self.camera is not None:
            data["camera"] = self.camera
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageRecord":
        return cls(
            id=int(data["id"]),
            file_name=str(data["file_name"]),
            width=int(data["width"]),
            height=int(data["height"]),
            capture_group=data.get("capture_group"),
            camera=data.get("camera"),
        )


@dataclass
class Annotation:
    id: int
    image_id: int
    category_id: int
    bbox: list[float]
    area: float
    score: float | None = None
    iscrowd: int = 0

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "image_id": self.image_id,
            "category_id": self.category_id,
            "bbox": self.bbox,
            "area": self.area,
            "iscrowd": self.iscrowd,
        }
        if self.score is not None:
            data["score"] = self.score
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Annotation":
        return cls(
            id=int(data["id"]),
            image_id=int(data["image_id"]),
            category_id=int(data["category_id"]),
            bbox=[float(value) for value in data["bbox"]],
            area=float(data.get("area", 0.0)),
            score=float(data["score"]) if data.get("score") is not None else None,
            iscrowd=int(data.get("iscrowd", 0)),
        )


@dataclass
class CocoDataset:
    images: list[ImageRecord] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)

    def next_image_id(self) -> int:
        return max((image.id for image in self.images), default=0) + 1

    def next_annotation_id(self) -> int:
        return max((annotation.id for annotation in self.annotations), default=0) + 1

    def next_category_id(self) -> int:
        return max((category.id for category in self.categories), default=0) + 1

    def category_by_name(self, name: str) -> Category | None:
        normalized = name.strip().casefold()
        for category in self.categories:
            if category.name.strip().casefold() == normalized:
                return category
        return None

    def ensure_category(self, name: str) -> Category:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Klassnamn far inte vara tomt")
        existing = self.category_by_name(cleaned)
        if existing is not None:
            return existing
        category = Category(id=self.next_category_id(), name=cleaned)
        self.categories.append(category)
        return category

    def annotations_for_image(self, image_id: int) -> list[Annotation]:
        return [annotation for annotation in self.annotations if annotation.image_id == image_id]

    def validate(self) -> None:
        image_ids = {image.id for image in self.images}
        if len(image_ids) != len(self.images):
            raise ValueError("COCO innehaller dubblerade bild-id")
        category_ids = {category.id for category in self.categories}
        if len(category_ids) != len(self.categories):
            raise ValueError("COCO innehaller dubblerade kategori-id")
        annotation_ids = {annotation.id for annotation in self.annotations}
        if len(annotation_ids) != len(self.annotations):
            raise ValueError("COCO innehaller dubblerade annotations-id")
        for annotation in self.annotations:
            if annotation.image_id not in image_ids:
                raise ValueError(f"Annotation {annotation.id} refererar till okand bild")
            if annotation.category_id not in category_ids:
                raise ValueError(f"Annotation {annotation.id} refererar till okand kategori")
            if len(annotation.bbox) != 4:
                raise ValueError("COCO bbox maste ha fyra varden")
            if annotation.bbox[2] < 0 or annotation.bbox[3] < 0:
                raise ValueError("COCO bbox bredd och hojd far inte vara negativa")

    def to_dict(self) -> dict[str, Any]:
        return {
            "images": [image.to_dict() for image in self.images],
            "annotations": [annotation.to_dict() for annotation in self.annotations],
            "categories": [category.to_dict() for category in self.categories],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CocoDataset":
        dataset = cls(
            images=[ImageRecord.from_dict(item) for item in data.get("images", [])],
            annotations=[Annotation.from_dict(item) for item in data.get("annotations", [])],
            categories=[Category.from_dict(item) for item in data.get("categories", [])],
        )
        dataset.validate()
        return dataset


def read_coco(path: Path | str) -> CocoDataset:
    return CocoDataset.from_dict(read_json(Path(path)))


def write_coco(dataset: CocoDataset, path: Path | str) -> None:
    dataset.validate()
    atomic_write_json(Path(path), dataset.to_dict())
