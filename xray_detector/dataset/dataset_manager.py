"""DatasetManager – hanterar datasetversioner, metadata och tillägg av bilder."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from xray_detector.dataset.coco import CocoDataset


class DatasetManager:
    """Hanterar COCO-datasetversioner under en rotkatalog."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- Versioner ----
    def list_versions(self) -> list[str]:
        """Returnera sorterad lista över befintliga versioner."""
        if not self.root.exists():
            return []
        return sorted(
            (p.name for p in self.root.iterdir()
             if p.is_dir() and (p / "annotations.json").exists()),
            key=lambda v: (len(v), v),
        )

    def next_version(self) -> str:
        """Nästa versionsnummer (v1, v2, ...)."""
        versions = self.list_versions()
        max_n = 0
        for v in versions:
            if v.startswith("v") and v[1:].isdigit():
                max_n = max(max_n, int(v[1:]))
        return f"v{max_n + 1}"

    def open(self, version: str) -> CocoDataset:
        """Öppna (ladda) en datasetversion."""
        ds = CocoDataset(self.root, version)
        ds.load()
        return ds

    def create_version(self, base_version: str | None = None,
                       categories: list[str] | None = None) -> CocoDataset:
        """Skapa en ny version. Kan klonas från en basversion."""
        version = self.next_version()
        ds = CocoDataset(self.root, version)
        ds.ensure_dirs()
        if base_version:
            src = self.open(base_version)
            # Klonar kategorier och metadata (inte bilder)
            ds.categories = list(src.categories)
            ds.meta = dict(src.meta)
            logger.info("Klonade kategorier från {}", base_version)
        if categories:
            for name in categories:
                ds.category_id_for(name)
        ds.meta["created"] = datetime.now().isoformat(timespec="seconds")
        ds.meta["base_version"] = base_version
        ds.save()
        logger.info("Skapade datasetversion {}", version)
        return ds

    def delete_version(self, version: str) -> None:
        d = self.root / version
        if d.exists():
            shutil.rmtree(d)
            logger.info("Raderade datasetversion {}", version)

    # ---- Tillägg av bilder ----
    def add_images(
        self,
        version: str,
        images: list[np.ndarray],
        annotations: list[list[dict]],
        source: str = "capture",
    ) -> int:
        """Lägg till bilder + annotations i en version.

        images: list av BGR-frames (np.ndarray)
        annotations: per bild, list av dict {class_name, x, y, w, h}
        Returnerar antal tillagda bilder.
        """
        ds = self.open(version)
        ds.ensure_dirs()
        added = 0
        for frame, anns in zip(images, annotations):
            if frame is None:
                continue
            h, w = frame.shape[:2]
            # Filnamn: timestamp + sekvens
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_name = f"{stamp}_{added:04d}.jpg"
            img_path = ds.images_dir / file_name
            cv2.imwrite(str(img_path), frame)
            img = ds.add_image(file_name, w, h)
            for a in anns:
                cat_id = ds.category_id_for(a["class_name"])
                ds.add_annotation(
                    image_id=img.id,
                    category_id=cat_id,
                    x=a["x"], y=a["y"], w=a["w"], h=a["h"],
                )
            added += 1
        ds.meta.setdefault("created", datetime.now().isoformat(timespec="seconds"))
        ds.meta["last_updated"] = datetime.now().isoformat(timespec="seconds")
        ds.meta["source"] = source
        ds.save()
        logger.info("Lade till {} bilder i {}", added, version)
        return added

    def metadata(self, version: str) -> dict:
        """Returnera metadata för en version."""
        meta_path = self.root / version / "meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": version, "num_images": 0, "num_objects": 0}
