from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2
import numpy as np

from src.core.models_schema import BoundingBox, DatasetVersionInfo
from src.dataset.exporters import export_dataset_version


class DatasetManager:
    """Hanterar det aktiva datasetet (i kanoniskt COCO-format) samt versionshanterade exporter."""

    def __init__(
        self,
        working_dir: str | Path = "data/working",
        exports_dir: str | Path = "data/datasets",
        default_classes: Optional[List[str]] = None,
    ) -> None:
        self.working_dir = Path(working_dir)
        self.exports_dir = Path(exports_dir)
        self.images_dir = self.working_dir / "images"
        self.coco_file = self.working_dir / "annotations.coco.json"

        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        self.default_classes = default_classes or [
            "Metallföremål",
            "Batteri",
            "Vätszebehållare",
            "Elektronik",
            "Okänt objekt",
        ]
        self.coco_data: Dict[str, Any] = self._load_or_init_coco()

    def _load_or_init_coco(self) -> Dict[str, Any]:
        if self.coco_file.exists():
            try:
                with open(self.coco_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "images" in data and "annotations" in data and "categories" in data:
                    return data
            except Exception:
                pass

        categories = [
            {"id": idx + 1, "name": name, "supercategory": "xray_object"}
            for idx, name in enumerate(self.default_classes)
        ]
        data = {
            "info": {
                "description": "X-ray Detector Working Dataset (COCO format)",
                "version": "working",
                "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "licenses": [],
            "categories": categories,
            "images": [],
            "annotations": [],
        }
        self._save_working_coco(data)
        return data

    def _save_working_coco(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is not None:
            self.coco_data = data
        self.coco_data["info"]["date_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.coco_data["info"]["num_images"] = len(self.coco_data.get("images", []))
        self.coco_data["info"]["num_objects"] = len(self.coco_data.get("annotations", []))
        with open(self.coco_file, "w", encoding="utf-8") as f:
            json.dump(self.coco_data, f, ensure_ascii=False, indent=2)

    def get_classes(self) -> List[str]:
        cats = sorted(self.coco_data.get("categories", []), key=lambda c: c["id"])
        return [c["name"] for c in cats]

    def ensure_class(self, class_name: str) -> int:
        """Returnerar category_id för klassen, eller skapar en ny klass om den inte finns."""
        clean_name = class_name.strip()
        if not clean_name:
            clean_name = "Okänt objekt"

        for cat in self.coco_data["categories"]:
            if cat["name"].lower() == clean_name.lower():
                return int(cat["id"])

        next_id = max([int(c["id"]) for c in self.coco_data["categories"]] + [0]) + 1
        self.coco_data["categories"].append(
            {"id": next_id, "name": clean_name, "supercategory": "xray_object"}
        )
        self._save_working_coco()
        return next_id

    def add_annotated_frame_pair(
        self,
        frame_1_bgr: np.ndarray,
        boxes_1: List[BoundingBox],
        frame_2_bgr: np.ndarray,
        boxes_2: List[BoundingBox],
    ) -> tuple[int, int]:
        """Sparar de två bilderna och deras annoterade rektanglar till datasetet.

        Returnerar (totalt_antal_bilder, totalt_antal_objekt) i working-datasetet.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self._add_single_image(frame_1_bgr, boxes_1, f"stream1_{timestamp}.png")
        self._add_single_image(frame_2_bgr, boxes_2, f"stream2_{timestamp}.png")
        self._save_working_coco()
        return self.get_working_stats()

    def _add_single_image(
        self,
        frame_bgr: np.ndarray,
        boxes: List[BoundingBox],
        filename: str,
    ) -> None:
        img_path = self.images_dir / filename
        cv2.imwrite(str(img_path), frame_bgr)
        h, w = frame_bgr.shape[:2]

        next_img_id = max([int(img["id"]) for img in self.coco_data["images"]] + [0]) + 1
        self.coco_data["images"].append(
            {
                "id": next_img_id,
                "file_name": filename,
                "width": w,
                "height": h,
                "date_captured": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        next_ann_id = max([int(ann["id"]) for ann in self.coco_data["annotations"]] + [0]) + 1
        for box in boxes:
            clamped = box.clamp(w, h)
            if clamped.width < 2 or clamped.height < 2:
                continue
            cat_id = self.ensure_class(clamped.class_name)
            coco_bbox = clamped.to_coco_bbox()
            self.coco_data["annotations"].append(
                {
                    "id": next_ann_id,
                    "image_id": next_img_id,
                    "category_id": cat_id,
                    "bbox": coco_bbox,
                    "area": round(clamped.area, 2),
                    "iscrowd": 0,
                }
            )
            next_ann_id += 1

    def get_working_stats(self) -> tuple[int, int]:
        """Returnerar (antal_bilder, antal_annoterade_objekt) i working-datasetet."""
        return len(self.coco_data.get("images", [])), len(self.coco_data.get("annotations", []))

    def list_exported_versions(self) -> List[DatasetVersionInfo]:
        """Listar alla exporterade dataset-versioner sorterade med senaste versionen först."""
        versions: List[DatasetVersionInfo] = []
        if not self.exports_dir.exists():
            return versions

        for child in self.exports_dir.iterdir():
            if not child.is_dir():
                continue
            manifest_path = child / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    versions.append(
                        DatasetVersionInfo(
                            version=int(m["version"]),
                            created_at=str(m["created_at"]),
                            export_format=str(m.get("export_format", "COCO+YOLO")),
                            num_images=int(m.get("num_images", 0)),
                            num_objects=int(m.get("num_objects", 0)),
                            classes=list(m.get("classes", [])),
                            path=str(child),
                        )
                    )
                except Exception:
                    continue

        versions.sort(key=lambda v: v.version, reverse=True)
        return versions

    def get_next_version_number(self) -> int:
        existing = self.list_exported_versions()
        if not existing:
            return 1
        return max(v.version for v in existing) + 1

    def export_new_version(self, export_format: str = "COCO+YOLO") -> DatasetVersionInfo:
        """Skapar och exporterar en ny versionssiffra av datasetet i valt format (COCO, YOLO eller COCO+YOLO)."""
        version_num = self.get_next_version_number()
        manifest = export_dataset_version(
            working_dir=self.working_dir,
            exports_dir=self.exports_dir,
            coco_data=self.coco_data,
            version=version_num,
            export_format=export_format,
        )
        return DatasetVersionInfo(
            version=int(manifest["version"]),
            created_at=str(manifest["created_at"]),
            export_format=str(manifest["export_format"]),
            num_images=int(manifest["num_images"]),
            num_objects=int(manifest["num_objects"]),
            classes=list(manifest["classes"]),
            path=str(manifest["path"]),
        )
