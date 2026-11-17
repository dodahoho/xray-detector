import json
import logging
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import cv2

from xray_detector.domain.dataset import (
    AnnotatedImage,
    VariationSettings,
    capture_group,
)
from xray_detector.infrastructure.dataset_store.augment import (
    apply_variations,
    variation_plan,
)
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


def _pair_count(images: list[dict]) -> int:
    """Antal fångstgrupper (bildpar) i en lista bilder."""
    return len({capture_group(image) for image in images})


def _is_metadata(payload: object) -> bool:
    """Om det inlästa värdet har den form _save_metadata skriver."""
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("info"), dict)
        and isinstance(payload.get("images"), list)
    )


def _warn_broken_metadata(path: Path, reason: object) -> None:
    logging.getLogger("xray").warning(
        "%s går inte att läsa (%s); datasetet startar tomt", path.name, reason
    )


class DatasetStore:
    """YOLO-dataset på en katalog: data.yaml, images/ och labels/.

    Annoteringarna ligger i YOLO-format i labels/ och klasserna i data.yaml.
    dataset.json innehåller bara det YOLO saknar: bild-id, bildstorlek,
    fångstgrupp och fångsttid, som vyerna grupperar och sorterar på.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

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
        """Läser dataset.json; en trasig fil ger ett tomt dataset och en varning.

        Skrivningen är atomisk, men filen kan ändå bli oläsbar av ett avbrott
        eller en manuell redigering. Ett tomt dataset låter appen starta och
        nästa skrivning ersätter filen, i stället för att felet propagerar upp
        genom MainWindow.__init__ så att fönstret aldrig visas (TASK-124).
        """
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, encoding="utf-8") as file:
                    metadata = json.load(file)
            except (OSError, ValueError) as error:
                _warn_broken_metadata(self.metadata_path, error)
            else:
                if _is_metadata(metadata):
                    return metadata
                _warn_broken_metadata(self.metadata_path, "saknar info eller images")
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
        metadata["info"]["num_objects"] = self._object_count(metadata["images"])
        atomic_write_json(self.metadata_path, metadata)

    def _object_count(self, images: list[dict]) -> int:
        """Antal annoteringar i labels/ för bilderna (TASK-126).

        Räknas ur label-filerna i stället för att underhållas inkrementellt i
        varje operation, så det sparade värdet alltid stämmer med datasetet.
        """
        return sum(len(read_labels(self._label_path(image["file_name"]))) for image in images)

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

    def unused_classes(self) -> list[str]:
        """Klasser i data.yaml som ingen annotering använder (TASK-109).

        Läses i en svepning över labels/ i stället för en sökning per klass, så
        en lång klasslista inte kostar en genomläsning av datasetet per namn.
        """
        names = self.classes()
        if not self.labels_dir.exists():
            return list(names)
        used: set[int] = set()
        for path in self.labels_dir.glob("*.txt"):
            used.update(row[0] for row in read_labels(path))
        return [name for index, name in enumerate(names) if index not in used]

    def remove_unused_classes(self) -> list[str]:
        """Rensar klasslistan till de klasser som finns annoterade (TASK-109).

        set_classes skriver om labelindexen, så de klasser som blir kvar
        behåller sina annoteringar. Returnerar de borttagna namnen.
        """
        removed = self.unused_classes()
        if removed:
            self.set_classes([name for name in self.classes() if name not in removed])
        return removed

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
            image_id += 1
        if names != known:
            write_data_yaml(self.data_yaml, names)
        self._save_metadata(metadata)

    def replace_samples(
        self,
        image_ids: list[int],
        samples: list[AnnotatedImage],
    ) -> None:
        """Skriver om sparade bilder på plats i stället för att lägga till kopior (TASK-110).

        Bild-id, fångstgrupp, fångsttid och synthetic/source behålls, så ett
        redigerat bildpar ligger kvar på samma plats i datasetet och en
        variation fortsätter höra till sitt ursprung. Stämmer antalet bilder
        inte med antalet id:n raderas de gamla och bilderna läggs till som nya.
        """
        metadata = self._load_metadata()
        by_id = {image["id"]: image for image in metadata["images"]}
        targets = [by_id[image_id] for image_id in image_ids if image_id in by_id]
        if len(targets) != len(samples):
            self.delete_images(image_ids)
            self.add_samples(samples)
            return
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        names = self.classes()
        known = list(names)
        for image, sample in zip(targets, samples, strict=True):
            label = self._label_path(image["file_name"])
            cv2.imwrite(str(self.images_dir / image["file_name"]), sample.frame)
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
            write_labels(label, rows)
            image["width"] = width
            image["height"] = height
        if names != known:
            write_data_yaml(self.data_yaml, names)
        self._save_metadata(metadata)

    def add_variations(
        self,
        settings: VariationSettings,
        seed: int | None = None,
    ) -> int:
        """Utökar datasetet med syntetiska variationer av originalbilderna (TASK-88).

        Varje variation blir en egen fångstgrupp med samma bilder som
        originalet, så bildparet hålls ihop och variationen syns som ett eget
        kort. Bara originalbilderna varieras, så en ny utökning inte varierar
        en tidigare variation. Returvärdet är antalet tillagda bildpar.
        """
        dataset = self.load_dataset()
        originals = [
            image for image in dataset["images"] if not image.get("synthetic")
        ]
        if not originals or settings.total == 0:
            return 0
        groups: dict[object, list[dict]] = {}
        for image in originals:
            groups.setdefault(image.get("group") or image["id"], []).append(image)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        metadata = self._load_metadata()
        image_id = max((img["id"] for img in metadata["images"]), default=0) + 1
        group_id = max((img.get("group", 0) for img in metadata["images"]), default=0) + 1
        names = self.classes()
        known = list(names)
        added = 0
        rng = random.Random(seed)
        for key in sorted(groups, key=str):
            members = sorted(groups[key], key=lambda img: img["id"])
            # originalet läses en gång och återanvänds för alla variationer
            frames = [
                (image, cv2.imread(str(self.images_dir / image["file_name"])))
                for image in members
            ]
            frames = [(image, frame) for image, frame in frames if frame is not None]
            if not frames:
                continue
            for variations in variation_plan(settings, rng):
                for image, frame in frames:
                    varied, annotations = apply_variations(
                        frame, image["annotations"], variations
                    )
                    image_name = f"img_{image_id:06d}.png"
                    cv2.imwrite(str(self.images_dir / image_name), varied)
                    height, width = varied.shape[:2]
                    rows = [
                        from_pixels(
                            self._class_index(names, annotation["class_name"]),
                            annotation["bbox"],
                            width,
                            height,
                        )
                        for annotation in annotations
                    ]
                    write_labels(self._label_path(image_name), rows)
                    metadata["images"].append(
                        {
                            "id": image_id,
                            "file_name": image_name,
                            "width": width,
                            "height": height,
                            "group": group_id,
                            "captured": image.get("captured"),
                            "synthetic": True,
                            "source": image["id"],
                            "variation": variations,
                        }
                    )
                    image_id += 1
                group_id += 1
                added += 1
        if names != known:
            write_data_yaml(self.data_yaml, names)
        self._save_metadata(metadata)
        return added

    def delete_synthetic(self) -> int:
        """Tar bort alla syntetiska bilder; returnerar antalet borttagna bilder (TASK-88)."""
        ids = [
            image["id"]
            for image in self._load_metadata()["images"]
            if image.get("synthetic")
        ]
        if ids:
            self.delete_images(ids)
        return len(ids)

    def metadata(self) -> dict:
        return self._load_metadata()["info"]

    def dataset_counts(self) -> tuple[int, int]:
        """Antal ursprungsbildpar och antal syntetiska bildpar (TASK-108).

        Räknas på metadata, så siffrorna är desamma som delningen utgår från:
        en syntetisk bild hör till sitt ursprungs bildpar och lägger därför
        inte till ett par. Varje variation blir en egen fångstgrupp, så de
        syntetiska bildparen är antalet grupper bland de syntetiska bilderna.
        """
        images = self._load_metadata()["images"]
        originals = [image for image in images if not image.get("synthetic")]
        synthetic = [image for image in images if image.get("synthetic")]
        return _pair_count(originals), _pair_count(synthetic)

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
        for image in removed:
            self._label_path(image["file_name"]).unlink(missing_ok=True)
            (self.images_dir / image["file_name"]).unlink(missing_ok=True)
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
