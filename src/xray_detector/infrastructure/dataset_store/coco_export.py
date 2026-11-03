"""COCO dataset export."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from xray_detector.infrastructure.dataset_store.coco_store import CocoStore, _atomic_write_json


def export_coco(store: CocoStore, version: str, destination: Path) -> dict:
    """Export a frozen version as a plain COCO dataset with a manifest."""
    coco = store.load_version(version)
    manifest = store.version_manifest(version)
    destination.mkdir(parents=True, exist_ok=True)
    images_dir = destination / "images"
    store.copy_images(coco, images_dir)

    export_manifest = {
        "format": "coco",
        "dataset": store.name,
        "version": version,
        "exported_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "image_count": manifest["image_count"],
        "pair_count": manifest["pair_count"],
        "annotation_count": manifest["annotation_count"],
        "category_counts": manifest["category_counts"],
        "source_created_at": manifest["created_at"],
        "class_names": [
            category["name"]
            for category in sorted(coco.get("categories", []), key=lambda item: item["id"])
        ],
    }
    _atomic_write_json(destination / "annotations" / "instances.json", coco)
    _atomic_write_json(destination / "manifest.json", export_manifest)
    return export_manifest


def export_coco_to_directory(store: CocoStore, version: str, destination: Path) -> Path:
    """Export COCO and return the export directory (convenience wrapper)."""
    export_coco(store, version, destination)
    return destination


__all__ = ["export_coco", "export_coco_to_directory"]
