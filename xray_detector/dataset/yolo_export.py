"""Exportera COCO-dataset till YOLO-format (labels + data.yaml).

YOLO-format:
    <version>/yolo/
        images/      # (symlänkar eller kopierar bilder)
        labels/      # 000001.txt med "class cx cy w h" (normaliserat)
        data.yaml    # {path, train, val, names: [...]}
"""
from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

from xray_detector.dataset.coco import CocoDataset


def export_yolo(ds: CocoDataset, copy_images: bool = True) -> Path:
    """Exportera en COCO-datasetversion till YOLO-format.

    Returnerar path till yolo-mappen.
    """
    yolo_dir = ds.dir / "yolo"
    images_dir = yolo_dir / "images"
    labels_dir = yolo_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    # Bygg namn-mapping: category_id → index (sorterat efter id)
    cat_sorted = sorted(ds.categories, key=lambda c: c.id)
    cat_to_idx = {c.id: i for i, c in enumerate(cat_sorted)}
    names = [c.name for c in cat_sorted]

    # Skriv labels
    for img in ds.images:
        img_anns = [a for a in ds.annotations if a.image_id == img.id]
        label_lines = []
        for a in img_anns:
            x, y, w, h = a.bbox
            # Normalisera till center + wh
            cx = (x + w / 2) / img.width
            cy = (y + h / 2) / img.height
            nw = w / img.width
            nh = h / img.height
            cls_idx = cat_to_idx.get(a.category_id, 0)
            label_lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
        label_path = labels_dir / (Path(img.file_name).stem + ".txt")
        label_path.write_text("\n".join(label_lines), encoding="utf-8")

        # Kopiera/symlänka bild
        src = ds.images_dir / img.file_name
        dst = images_dir / img.file_name
        if src.exists() and not dst.exists():
            if copy_images:
                shutil.copy2(src, dst)
            else:
                dst.symlink_to(src)

    # data.yaml
    data = {
        "path": str(ds.dir),
        "train": "yolo/images",
        "val": "yolo/images",
        "names": names,
    }
    (yolo_dir / "data.yaml").write_text(
        _to_yaml(data), encoding="utf-8"
    )
    logger.info("Exporterade {} till YOLO-format: {}", ds.version, yolo_dir)
    return yolo_dir


def _to_yaml(data: dict) -> str:
    """Enkel YAML-serialisering (undviker pyyaml-beroende här)."""
    lines = []
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines) + "\n"
