# -*- coding: utf-8 -*-
"""Patch (TASK-11): RF-DETR-export + familj i träningspipelinen."""
import re

# ---- export.py: export_rfdetr
path = "xray_detector/infrastructure/dataset_store/export.py"
text = open(path, encoding="utf-8").read()
assert "export_rfdetr" not in text
text += '''

def _coco_for_split(coco: dict, images: list[dict]) -> dict:
    """COCO-dokument för en delmängd bilder (RF-DETR:s per-split json)."""
    ids = {image["id"] for image in images}
    return {
        "info": dict(coco.get("info", {})),
        "licenses": coco.get("licenses", []),
        "categories": coco["categories"],
        "images": [dict(image) for image in images],
        "annotations": [
            dict(annotation) for annotation in coco["annotations"]
            if annotation["image_id"] in ids
        ],
    }


def export_rfdetr(store: DatasetStore, version: int, export_root: Path) -> Path:
    """Exporterar i RF-DETR:s forvantalade format: train/valid/test med _annotations.coco.json."""
    import json

    coco = store.load_coco(version)
    out_dir = export_root / f"v{version}_rfdetr"
    source_images = store.version_dir(version) / "images"
    train, val = train_val_split(coco)

    for split, images in (("train", train), ("valid", val), ("test", val)):
        split_dir = out_dir / split
        (split_dir / "images").mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(
                source_images / image["file_name"],
                split_dir / "images" / image["file_name"],
            )
        split_coco = _coco_for_split(coco, images)
        for image in split_coco["images"]:
            image["file_name"] = f"images/{image['file_name']}"
        with open(split_dir / "_annotations.coco.json", "w", encoding="utf-8") as file:
            json.dump(split_coco, file, ensure_ascii=False, indent=2)

    write_manifest(out_dir, coco, version, "rfdetr",
                   num_train=len(train), num_val=len(val), num_test=len(val))
    return out_dir
'''
open(path, "w", encoding="utf-8", newline="").write(text)
print("export_rfdetr lagd")

# ---- dataset_service: fasad
path = "xray_detector/application/dataset_service.py"
text = open(path, encoding="utf-8").read()
text = text.replace(
    "from xray_detector.infrastructure.dataset_store.export import (\n    SPLIT_RATIO,\n    SPLIT_SEED,\n    export_coco,\n    export_yolo,\n    train_val_split,\n)",
    "from xray_detector.infrastructure.dataset_store.export import (\n    SPLIT_RATIO,\n    SPLIT_SEED,\n    export_coco,\n    export_rfdetr,\n    export_yolo,\n    train_val_split,\n)",
)
assert "export_rfdetr" in text
text = text.replace(
    "    def export_coco(self, version: int, export_root: Path) -> Path:\n        return export_coco(self.store, version, export_root)\n",
    "    def export_coco(self, version: int, export_root: Path) -> Path:\n        return export_coco(self.store, version, export_root)\n\n    def export_rfdetr(self, version: int, export_root: Path) -> Path:\n        return export_rfdetr(self.store, version, export_root)\n",
)
assert text.count("export_rfdetr") == 2
open(path, "w", encoding="utf-8", newline="").write(text)
print("dataset_service-fasad lagd")
