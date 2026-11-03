from __future__ import annotations

from datetime import datetime
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
import yaml


def export_dataset_version(
    working_dir: Path,
    exports_dir: Path,
    coco_data: Dict[str, Any],
    version: int,
    export_format: str = "COCO+YOLO",
) -> Dict[str, Any]:
    """Exporterar en versionshanterad snapshot av datasetet till COCO, YOLO eller båda.

    Säkerställer att det tydligt framgår:
    - Versionssiffra (`version`)
    - Datum (`created_at`)
    - Antal bilder (`num_images`) och antal bildobjekt (`num_objects`)
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_slug = datetime.now().strftime("%Y-%m-%d")
    version_dir_name = f"v{version}_{date_slug}"
    target_dir = exports_dir / version_dir_name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    images: List[Dict[str, Any]] = coco_data.get("images", [])
    annotations: List[Dict[str, Any]] = coco_data.get("annotations", [])
    categories: List[Dict[str, Any]] = coco_data.get("categories", [])

    num_images = len(images)
    num_objects = len(annotations)
    class_names = [c["name"] for c in sorted(categories, key=lambda x: x["id"])]
    cat_id_to_idx = {c["id"]: idx for idx, c in enumerate(sorted(categories, key=lambda x: x["id"]))}

    # Kopiera bildfiler till versionens images-mapp
    src_images_dir = working_dir / "images"
    dst_images_dir = target_dir / "images"
    dst_images_dir.mkdir(parents=True, exist_ok=True)
    for img_entry in images:
        fname = img_entry["file_name"]
        src_path = src_images_dir / fname
        if src_path.exists():
            shutil.copy2(src_path, dst_images_dir / fname)

    fmt_upper = export_format.upper()

    # 1. Skriv COCO JSON om COCO eller COCO+YOLO
    if "COCO" in fmt_upper:
        coco_export = {
            "info": {
                "description": f"X-ray Detector Dataset v{version}",
                "version": str(version),
                "version_number": version,
                "date_created": now_str,
                "num_images": num_images,
                "num_objects": num_objects,
            },
            "licenses": [],
            "categories": categories,
            "images": images,
            "annotations": annotations,
        }
        coco_path = target_dir / "annotations.coco.json"
        with open(coco_path, "w", encoding="utf-8") as f:
            json.dump(coco_export, f, ensure_ascii=False, indent=2)

    # 2. Skriv YOLO-format (labels/*.txt + data.yaml) om YOLO eller COCO+YOLO
    if "YOLO" in fmt_upper:
        labels_dir = target_dir / "labels"
        labels_dir.mkdir(parents=True, exist_ok=True)

        img_map = {img["id"]: img for img in images}
        anns_by_img: Dict[int, List[Dict[str, Any]]] = {img["id"]: [] for img in images}
        for ann in annotations:
            img_id = ann["image_id"]
            if img_id in anns_by_img:
                anns_by_img[img_id].append(ann)

        for img_id, img_info in img_map.items():
            img_w = max(1, int(img_info.get("width", 1)))
            img_h = max(1, int(img_info.get("height", 1)))
            stem = Path(img_info["file_name"]).stem
            label_file = labels_dir / f"{stem}.txt"

            lines: List[str] = []
            for ann in anns_by_img.get(img_id, []):
                cat_id = ann["category_id"]
                yolo_cls_idx = cat_id_to_idx.get(cat_id, 0)
                bbox = ann.get("bbox", [0, 0, 0, 0])  # [x, y, w, h] i pixlar
                x, y, bw, bh = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                x_center = max(0.0, min(1.0, (x + bw / 2.0) / img_w))
                y_center = max(0.0, min(1.0, (y + bh / 2.0) / img_h))
                norm_w = max(0.0, min(1.0, bw / img_w))
                norm_h = max(0.0, min(1.0, bh / img_h))
                lines.append(f"{yolo_cls_idx} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}")

            with open(label_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + ("\n" if lines else ""))

        yolo_yaml = {
            "path": str(target_dir.resolve()),
            "train": "images",
            "val": "images",
            "nc": len(class_names),
            "names": {i: name for i, name in enumerate(class_names)},
            "dataset_info": {
                "version": version,
                "date_created": now_str,
                "num_images": num_images,
                "num_objects": num_objects,
            },
        }
        with open(target_dir / "data.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(yolo_yaml, f, allow_unicode=True, sort_keys=False)

    # 3. Skriv manifest.json och läsbar versionsfil
    manifest = {
        "version": version,
        "created_at": now_str,
        "export_format": export_format,
        "num_images": num_images,
        "num_objects": num_objects,
        "classes": class_names,
        "path": str(target_dir),
    }
    with open(target_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    summary_txt = (
        f"X-RAY DETECTOR DATASET EXPORT\n"
        f"=============================\n"
        f"Versionssiffra : v{version}\n"
        f"Datum          : {now_str}\n"
        f"Format         : {export_format}\n"
        f"Antal bilder   : {num_images}\n"
        f"Antal objekt   : {num_objects}\n"
        f"Klasser ({len(class_names)})   : {', '.join(class_names)}\n"
    )
    with open(target_dir / "VERSION_INFO.txt", "w", encoding="utf-8") as f:
        f.write(summary_txt)

    return manifest
