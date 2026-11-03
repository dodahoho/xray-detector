"""COCO-backed dataset store with immutable version snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from xray_detector.domain.annotation import AnnotationBox
from xray_detector.domain.dataset import DatasetInfo, DatasetVersionSummary


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _coco_hash(coco: dict[str, Any]) -> str:
    payload = json.dumps(coco, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _empty_coco(name: str) -> dict[str, Any]:
    created = utc_now()
    return {
        "info": {
            "description": f"X-ray detector dataset: {name}",
            "version": None,
            "date_created": created,
            "year": datetime.now(UTC).year,
            "contributor": "X-ray detector",
        },
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": [],
    }


class CocoStore:
    """Read/write a COCO dataset and create versioned snapshots."""

    def __init__(self, dataset_dir: Path, name: str | None = None) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.name = name or self.dataset_dir.name
        self.images_dir = self.dataset_dir / "images"
        self.annotations_dir = self.dataset_dir / "annotations"
        self.versions_dir = self.dataset_dir / "versions"
        self.meta_path = self.dataset_dir / "meta.json"
        self.current_path = self.annotations_dir / "instances.json"

    def ensure(self) -> None:
        for path in (self.images_dir, self.annotations_dir, self.versions_dir):
            path.mkdir(parents=True, exist_ok=True)
        if not self.meta_path.exists():
            meta = {
                "name": self.name,
                "created_at": utc_now(),
                "latest_version": None,
                "next_version": 1,
            }
            _atomic_write_json(self.meta_path, meta)
        if not self.current_path.exists():
            _atomic_write_json(self.current_path, _empty_coco(self.name))

    def meta(self) -> dict[str, Any]:
        self.ensure()
        return _read_json(self.meta_path)

    def info(self) -> DatasetInfo:
        meta = self.meta()
        return DatasetInfo(
            name=meta["name"],
            path=str(self.dataset_dir),
            created_at=meta["created_at"],
            latest_version=meta.get("latest_version"),
            next_version=meta.get("next_version", 1),
        )

    def current_coco(self) -> dict[str, Any]:
        self.ensure()
        return _read_json(self.current_path)

    def save_current(self, coco: dict[str, Any]) -> None:
        _atomic_write_json(self.current_path, coco)

    def list_versions(self) -> list[DatasetVersionSummary]:
        self.ensure()
        summaries: list[DatasetVersionSummary] = []
        for path in sorted(self.versions_dir.glob("v*.json")):
            try:
                payload = _read_json(path)
                manifest = payload.get("manifest", {})
                summaries.append(
                    DatasetVersionSummary(
                        version=manifest.get("version", path.stem),
                        created_at=manifest.get("created_at", ""),
                        image_count=manifest.get("image_count", 0),
                        pair_count=manifest.get("pair_count", 0),
                        annotation_count=manifest.get("annotation_count", 0),
                        category_counts=manifest.get("category_counts", {}),
                    )
                )
            except (OSError, json.JSONDecodeError):
                continue
        return summaries

    def load_version(self, version: str) -> dict[str, Any]:
        self.ensure()
        path = self.versions_dir / f"{version}.json"
        if not path.exists():
            raise FileNotFoundError(f"Dataset version not found: {version}")
        payload = _read_json(path)
        return payload["coco"]

    def version_manifest(self, version: str) -> dict[str, Any]:
        path = self.versions_dir / f"{version}.json"
        if not path.exists():
            raise FileNotFoundError(f"Dataset version not found: {version}")
        return _read_json(path)["manifest"]

    def category_names(self) -> list[str]:
        coco = self.current_coco()
        return sorted(category["name"] for category in coco.get("categories", []))

    def add_pair(
        self,
        frames: dict[str, np.ndarray],
        annotations: dict[str, list[AnnotationBox]],
        source: dict[str, Any] | None = None,
        jpeg_quality: int = 95,
        pair_id: str | None = None,
        min_box_size: int = 1,
    ) -> DatasetVersionSummary:
        """Append a pair of images + annotations and create a new version."""
        self.ensure()
        if set(frames) != {"cam0", "cam1"}:
            raise ValueError("A dataset pair requires exactly cam0 and cam1 frames")

        coco = self.current_coco()
        coco.setdefault("images", [])
        coco.setdefault("annotations", [])
        coco.setdefault("categories", [])

        category_by_name = {c["name"]: c for c in coco["categories"]}
        next_category_id = max((c["id"] for c in coco["categories"]), default=0) + 1
        next_image_id = max((i["id"] for i in coco["images"]), default=0) + 1
        next_annotation_id = max((a["id"] for a in coco["annotations"]), default=0) + 1

        pair_id = pair_id or uuid.uuid4().hex[:12]
        captured_at = utc_now()
        source = source or {}

        for role in ("cam0", "cam1"):
            frame = frames[role]
            if frame is None or frame.size == 0:
                raise ValueError(f"Empty frame for {role}")
            height, width = frame.shape[:2]
            file_name = f"{pair_id}_{role}.jpg"
            image_path = self.images_dir / file_name
            ok, encoded = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
            )
            if not ok:
                raise RuntimeError(f"Failed to encode image for {role}")
            encoded.tofile(image_path)

            image_record = {
                "id": next_image_id,
                "file_name": file_name,
                "width": int(width),
                "height": int(height),
                "pair_id": pair_id,
                "camera_role": role,
                "captured_at": captured_at,
            }
            image_record.update(source)
            coco["images"].append(image_record)

            for annotation in annotations.get(role, []):
                class_name = annotation.class_name.strip()
                if not class_name:
                    continue
                bbox = annotation.bbox.clip(width, height)
                if not bbox.is_valid(min_size=float(min_box_size)):
                    continue
                category = category_by_name.get(class_name)
                if category is None:
                    category = {
                        "id": next_category_id,
                        "name": class_name,
                        "supercategory": "object",
                    }
                    next_category_id += 1
                    coco["categories"].append(category)
                    category_by_name[class_name] = category

                x, y, w, h = bbox.to_xywh()
                record = {
                    "id": next_annotation_id,
                    "image_id": next_image_id,
                    "category_id": category["id"],
                    "bbox": [round(x, 2), round(y, 2), round(w, 2), round(h, 2)],
                    "area": round(bbox.area, 2),
                    "iscrowd": 0,
                }
                if annotation.score is not None:
                    record["score"] = round(float(annotation.score), 5)
                coco["annotations"].append(record)
                next_annotation_id += 1

            next_image_id += 1

        meta = self.meta()
        version_number = int(meta.get("next_version", 1))
        version = f"v{version_number:06d}"
        coco["info"]["version"] = version
        coco["info"]["date_created"] = captured_at

        category_counts: dict[str, int] = {}
        id_to_name = {c["id"]: c["name"] for c in coco["categories"]}
        for annotation in coco["annotations"]:
            name = id_to_name.get(annotation["category_id"], "unknown")
            category_counts[name] = category_counts.get(name, 0) + 1

        pair_ids = {image.get("pair_id") for image in coco["images"]}
        manifest = {
            "dataset": self.name,
            "version": version,
            "created_at": captured_at,
            "image_count": len(coco["images"]),
            "pair_count": len(pair_ids),
            "annotation_count": len(coco["annotations"]),
            "category_counts": dict(sorted(category_counts.items())),
            "coco_sha256": _coco_hash(coco),
        }

        _atomic_write_json(
            self.versions_dir / f"{version}.json", {"manifest": manifest, "coco": coco}
        )
        _atomic_write_json(self.current_path, coco)

        meta["latest_version"] = version
        meta["next_version"] = version_number + 1
        _atomic_write_json(self.meta_path, meta)

        return DatasetVersionSummary(
            version=version,
            created_at=captured_at,
            image_count=manifest["image_count"],
            pair_count=manifest["pair_count"],
            annotation_count=manifest["annotation_count"],
            category_counts=manifest["category_counts"],
        )

    def copy_images(self, coco: dict[str, Any], destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        for image in coco.get("images", []):
            source = self.images_dir / image["file_name"]
            if source.exists():
                shutil.copy2(source, destination / image["file_name"])


def discover_datasets(datasets_dir: Path) -> list[CocoStore]:
    if not datasets_dir.exists():
        return []
    stores = []
    for path in sorted(datasets_dir.iterdir()):
        if path.is_dir() and (path / "meta.json").exists():
            stores.append(CocoStore(path))
    return stores
