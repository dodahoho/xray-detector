import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import cv2

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json


def _migrate_versions(root: Path) -> None:
    """Flyttar upp den nyaste v<N>-katalogen till roten (TASK-57).

    Datasetversionerna togs bort, så det dataset som låg under den högsta
    versionen blir det enda datasetet. Äldre versioner lämnas orörda.
    """
    if (root / "dataset.json").exists() or (root / "images").exists():
        return
    versions = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir() and path.name.startswith("v") and path.name[1:].isdigit()
        ),
        key=lambda path: int(path.name[1:]),
    )
    if not versions:
        return
    newest = versions[-1]
    for name in ("dataset.json", "images"):
        source = newest / name
        if source.exists():
            shutil.move(str(source), str(root / name))
    shutil.rmtree(newest, ignore_errors=True)


class DatasetStore:
    """COCO-dataset på en katalog: dataset.json och images/."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        _migrate_versions(self.root)

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    def _load_coco(self) -> dict:
        path = self.root / "dataset.json"
        if path.exists():
            with open(path, encoding="utf-8") as file:
                return json.load(file)
        now = datetime.now(UTC).isoformat()
        return {
            "info": {
                "created": now,
                "updated": now,
                "num_images": 0,
                "num_objects": 0,
            },
            "categories": [],
            "images": [],
            "annotations": [],
        }

    def _save_coco(self, coco: dict) -> None:
        coco["info"]["updated"] = datetime.now(UTC).isoformat()
        coco["info"]["num_images"] = len(coco["images"])
        coco["info"]["num_objects"] = len(coco["annotations"])
        atomic_write_json(self.root / "dataset.json", coco)

    def _category_id(self, coco: dict, class_name: str) -> int:
        for category in coco["categories"]:
            if category["name"] == class_name:
                return category["id"]
        new_id = max((category["id"] for category in coco["categories"]), default=-1) + 1
        coco["categories"].append({"id": new_id, "name": class_name})
        return new_id

    def classes(self) -> list[str]:
        """Datasetets klasser (kategorierna); tomt innan datasetet har sparats."""
        return [category["name"] for category in self._load_coco()["categories"]]

    def has_dataset(self) -> bool:
        """Om dataset.json finns, det vill säga om datasetet har skrivits."""
        return (self.root / "dataset.json").exists()

    def set_classes(self, names: list[str]) -> None:
        """Sätter datasetets klasslista; id:t behålls för namn som finns kvar."""
        coco = self._load_coco()
        ids = {category["name"]: category["id"] for category in coco["categories"]}
        next_id = max(ids.values(), default=-1) + 1
        categories = []
        for name in names:
            if name not in ids:
                ids[name] = next_id
                next_id += 1
            categories.append({"id": ids[name], "name": name})
        coco["categories"] = categories
        self._save_coco(coco)

    def class_in_use(self, name: str) -> bool:
        """Om sparade annoteringar refererar klassen."""
        coco = self._load_coco()
        ids = {
            category["id"] for category in coco["categories"] if category["name"] == name
        }
        return any(
            annotation["category_id"] in ids for annotation in coco["annotations"]
        )

    def add_samples(
        self,
        samples: list[AnnotatedImage],
        captured: str | None = None,
    ) -> None:
        self.images_dir.mkdir(parents=True, exist_ok=True)
        coco = self._load_coco()
        image_id = max((img["id"] for img in coco["images"]), default=0) + 1
        annotation_id = max((ann["id"] for ann in coco["annotations"]), default=0) + 1
        group_id = max((img.get("group", 0) for img in coco["images"]), default=0) + 1
        stamp = captured or datetime.now(UTC).isoformat()
        for sample in samples:
            image_name = f"img_{image_id:06d}.png"
            cv2.imwrite(str(self.images_dir / image_name), sample.frame)
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
        self._save_coco(coco)

    def metadata(self) -> dict:
        return self._load_coco()["info"]

    def image_sizes(self) -> list[tuple[int, int, int]]:
        """Datasetets bildupplösningar som (bredd, höjd, antal) (TASK-80).

        Vanligaste upplösningen först; vid lika antal den större bilden, så
        träningens default bevarar detaljer när datasetet är blandat.
        """
        counts = Counter(
            (int(image["width"]), int(image["height"]))
            for image in self._load_coco()["images"]
            if image.get("width") and image.get("height")
        )
        return [
            (width, height, count)
            for (width, height), count in sorted(
                counts.items(), key=lambda item: (-item[1], -item[0][0] * item[0][1])
            )
        ]

    def delete_images(self, image_ids: list[int]) -> None:
        coco = self._load_coco()
        ids = set(image_ids)
        file_names = {
            img["file_name"] for img in coco["images"] if img["id"] in ids
        }
        coco["images"] = [img for img in coco["images"] if img["id"] not in ids]
        coco["annotations"] = [
            ann for ann in coco["annotations"] if ann["image_id"] not in ids
        ]
        self._save_coco(coco)
        for name in file_names:
            (self.images_dir / name).unlink(missing_ok=True)

    def load_coco(self) -> dict:
        return self._load_coco()
