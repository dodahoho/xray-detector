import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import cv2

from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json
from xray_detector.infrastructure.dataset_store.yolo import (
    DATA_YAML,
    from_pixels,
    label_name,
    read_classes,
    read_labels,
    to_pixels,
    write_data_yaml,
    write_labels,
)

METADATA_NAME = "dataset.json"


def _migrate_versions(root: Path) -> None:
    """Flyttar upp den nyaste v<N>-katalogen till roten (TASK-57).

    Datasetversionerna togs bort, så det dataset som låg under den högsta
    versionen blir det enda datasetet. Äldre versioner lämnas orörda.
    """
    if (root / METADATA_NAME).exists() or (root / "images").exists():
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
    for name in (METADATA_NAME, "images"):
        source = newest / name
        if source.exists():
            shutil.move(str(source), str(root / name))
    shutil.rmtree(newest, ignore_errors=True)


def _migrate_coco(root: Path) -> None:
    """Konverterar ett COCO-dataset till YOLO på plats (TASK-78).

    Ett dataset.json med annotations/categories skrivs om till enbart
    metadata: annoteringarna flyttas till labels/ och klasserna till
    data.yaml. dataset.json skrivs sist, så en avbruten migrering bara görs
    om nästa gång i stället för att lämna datasetet halvkonverterat.
    """
    path = root / METADATA_NAME
    if not path.exists():
        return
    try:
        with open(path, encoding="utf-8") as file:
            coco = json.load(file)
    except (OSError, ValueError):
        return
    if "annotations" not in coco and "categories" not in coco:
        return
    categories = sorted(coco.get("categories", []), key=lambda item: item["id"])
    names = [str(category["name"]) for category in categories]
    index_of = {
        category["id"]: index for index, category in enumerate(categories)
    }
    labels_dir = root / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    by_image: dict[int, list[dict]] = {}
    for annotation in coco.get("annotations", []):
        by_image.setdefault(annotation["image_id"], []).append(annotation)
    images = []
    for image in coco.get("images", []):
        width = int(image.get("width") or 0)
        height = int(image.get("height") or 0)
        rows = []
        if width and height:
            for annotation in by_image.get(image["id"], []):
                index = index_of.get(annotation["category_id"])
                if index is not None:
                    rows.append(from_pixels(index, annotation["bbox"], width, height))
        write_labels(labels_dir / label_name(image["file_name"]), rows)
        images.append(image)
    write_data_yaml(root / DATA_YAML, names)
    info = dict(coco.get("info", {}))
    info["num_images"] = len(images)
    info["num_objects"] = len(coco.get("annotations", []))
    atomic_write_json(path, {"info": info, "images": images})


class DatasetStore:
    """YOLO-dataset på en katalog: data.yaml, images/ och labels/.

    Annoteringarna ligger i YOLO-format i labels/ och klasserna i data.yaml.
    dataset.json innehåller bara det YOLO saknar: bild-id, bildstorlek,
    fångstgrupp och fångsttid, som vyerna grupperar och sorterar på.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        _migrate_versions(self.root)
        _migrate_coco(self.root)

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def labels_dir(self) -> Path:
        return self.root / "labels"

    @property
    def data_yaml(self) -> Path:
        return self.root / DATA_YAML

    @property
    def metadata_path(self) -> Path:
        return self.root / METADATA_NAME

    def _load_metadata(self) -> dict:
        if self.metadata_path.exists():
            with open(self.metadata_path, encoding="utf-8") as file:
                return json.load(file)
        now = datetime.now(UTC).isoformat()
        return {
            "info": {
                "created": now,
                "updated": now,
                "num_images": 0,
                "num_objects": 0,
            },
            "images": [],
        }

    def _save_metadata(self, metadata: dict) -> None:
        metadata["info"]["updated"] = datetime.now(UTC).isoformat()
        metadata["info"]["num_images"] = len(metadata["images"])
        atomic_write_json(self.metadata_path, metadata)

    def _label_path(self, file_name: str) -> Path:
        return self.labels_dir / label_name(file_name)

    @staticmethod
    def _class_index(names: list[str], class_name: str) -> int:
        """Klassens index i listan; en ny klass läggs sist."""
        if class_name not in names:
            names.append(class_name)
        return names.index(class_name)

    def classes(self) -> list[str]:
        """Datasetets klasser ur data.yaml; tomt innan datasetet har sparats."""
        return read_classes(self.data_yaml)

    def has_dataset(self) -> bool:
        """Om data.yaml finns, det vill säga om datasetet har skrivits."""
        return self.data_yaml.exists()

    def set_classes(self, names: list[str]) -> None:
        """Sätter klasslistan och skriver om labelindexen så de följer den.

        YOLO lagrar klassen som ett index i names-listan, så en borttagen
        klass mitt i listan flyttar alla senare index. Label-filerna skrivs
        därför om med den nya ordningen. En rad vars klass inte finns kvar
        tas bort, eftersom indexet inte längre betyder något.
        """
        old = self.classes()
        mapping = {
            index: names.index(name) for index, name in enumerate(old) if name in names
        }
        if mapping != {index: index for index in range(len(old))}:
            self._remap_labels(mapping)
        write_data_yaml(self.data_yaml, names)

    def _remap_labels(self, mapping: dict[int, int]) -> None:
        if not self.labels_dir.exists():
            return
        for path in self.labels_dir.glob("*.txt"):
            rows = read_labels(path)
            remapped = [
                (mapping[index], cx, cy, w, h)
                for index, cx, cy, w, h in rows
                if index in mapping
            ]
            if remapped != rows:
                write_labels(path, remapped)

    def class_in_use(self, name: str) -> bool:
        """Om sparade annoteringar refererar klassen."""
        names = self.classes()
        if name not in names or not self.labels_dir.exists():
            return False
        index = names.index(name)
        return any(
            row[0] == index
            for path in self.labels_dir.glob("*.txt")
            for row in read_labels(path)
        )

    def add_samples(
        self,
        samples: list[AnnotatedImage],
        captured: str | None = None,
    ) -> None:
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        metadata = self._load_metadata()
        image_id = max((img["id"] for img in metadata["images"]), default=0) + 1
        group_id = max((img.get("group", 0) for img in metadata["images"]), default=0) + 1
        stamp = captured or datetime.now(UTC).isoformat()
        names = self.classes()
        known = list(names)
        objects = 0
        for sample in samples:
            image_name = f"img_{image_id:06d}.png"
            cv2.imwrite(str(self.images_dir / image_name), sample.frame)
            height, width = sample.frame.shape[:2]
            rows = [
                from_pixels(
                    self._class_index(names, annotation["class_name"]),
                    annotation["bbox"],
                    width,
                    height,
                )
                for annotation in sample.annotations
            ]
            write_labels(self._label_path(image_name), rows)
            metadata["images"].append(
                {
                    "id": image_id,
                    "file_name": image_name,
                    "width": width,
                    "height": height,
                    "group": group_id,
                    "captured": stamp,
                }
            )
            objects += len(rows)
            image_id += 1
        if names != known:
            write_data_yaml(self.data_yaml, names)
        metadata["info"]["num_objects"] = metadata["info"].get("num_objects", 0) + objects
        self._save_metadata(metadata)

    def metadata(self) -> dict:
        return self._load_metadata()["info"]

    def image_sizes(self) -> list[tuple[int, int, int]]:
        """Datasetets bildupplösningar som (bredd, höjd, antal) (TASK-80).

        Vanligaste upplösningen först; vid lika antal den större bilden, så
        träningens default bevarar detaljer när datasetet är blandat.
        """
        counts = Counter(
            (int(image["width"]), int(image["height"]))
            for image in self._load_metadata()["images"]
            if image.get("width") and image.get("height")
        )
        return [
            (width, height, count)
            for (width, height), count in sorted(
                counts.items(), key=lambda item: (-item[1], -item[0][0] * item[0][1])
            )
        ]

    def delete_images(self, image_ids: list[int]) -> None:
        metadata = self._load_metadata()
        ids = set(image_ids)
        removed = [image for image in metadata["images"] if image["id"] in ids]
        metadata["images"] = [
            image for image in metadata["images"] if image["id"] not in ids
        ]
        objects = 0
        for image in removed:
            label = self._label_path(image["file_name"])
            objects += len(read_labels(label))
            label.unlink(missing_ok=True)
            (self.images_dir / image["file_name"]).unlink(missing_ok=True)
        metadata["info"]["num_objects"] = max(
            0, metadata["info"].get("num_objects", 0) - objects
        )
        self._save_metadata(metadata)

    def load_dataset(self) -> dict:
        """Datasetet som läsmodell: klasser och bilder med annoteringar i pixlar.

        Annoteringarna läses ur labels/ och räknas om till pixel-bboxar med
        bildens storlek, så vyerna slipper känna till YOLO-formatet.
        """
        metadata = self._load_metadata()
        names = self.classes()
        images = []
        for image in metadata["images"]:
            width = int(image.get("width") or 0)
            height = int(image.get("height") or 0)
            annotations = []
            if width and height:
                for row in read_labels(self._label_path(image["file_name"])):
                    index = row[0]
                    annotations.append(
                        {
                            "class_name": (
                                names[index] if index < len(names) else str(index)
                            ),
                            "bbox": to_pixels(row, width, height),
                        }
                    )
            images.append({**image, "annotations": annotations})
        return {"info": metadata["info"], "classes": names, "images": images}
