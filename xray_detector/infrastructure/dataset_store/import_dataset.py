"""Import av ett YOLO-dataset till appens dataset (TASK-159).

Ett YOLO-dataset är en katalog med data.yaml, images/ och labels/. Appens
lagring har samma layout, så importen kopierar bilderna och label-filerna
rakt in. YOLO-formatet saknar bildpar: appens export skriver därför
dataset.json bredvid, och när filen finns återställer importen bild-id,
fångstgrupp, fångsttid och den syntetiska bildens ursprung. Ett externt
dataset utan dataset.json importeras ändå, men då blir varje bild ett eget
bildpar.
"""

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2

from xray_detector.infrastructure.dataset_store.store import METADATA_NAME, DatasetStore
from xray_detector.infrastructure.dataset_store.yolo import (
    label_name,
    read_classes,
    read_data,
    read_labels,
    write_data_yaml,
    write_labels,
)

MODE_REPLACE = "replace"
MODE_EXTEND = "extend"
MODES = {MODE_REPLACE: "Ersätt befintligt", MODE_EXTEND: "Utöka befintligt"}

#: Filändelserna som räknas som bilder i ett YOLO-dataset.
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
#: Nycklarna i data.yaml som kan peka på en bildkatalog eller en bildlista.
SPLIT_KEYS = ("train", "val", "valid", "test")


@dataclass(frozen=True)
class ImportResult:
    """Vad importen lade till: antal bilder, bildpar och filer den hoppade över."""

    images: int
    pairs: int
    skipped: int = 0


def _images_in(directory: Path) -> list[Path]:
    """Bildfilerna under katalogen, rekursivt."""
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def _images_from_list(path: Path, root: Path) -> list[Path]:
    """Bildsökvägarna i en train.txt/val.txt, en per rad."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    images = []
    for line in lines:
        if not line.strip():
            continue
        entry = Path(line.strip())
        entry = entry if entry.is_absolute() else root / entry
        if entry.is_file():
            images.append(entry)
    return images


def _image_files(root: Path, data: dict) -> list[Path]:
    """Bilderna i datasetet: images/, data.yaml:s delmängder eller hela katalogen.

    Appens egen layout och exporten har images/ direkt under roten. Ett
    ultralytics-dataset kan i stället peka ut train/valid/test som kataloger
    eller som listfiler, så de läses när images/ saknas.
    """
    images_dir = root / "images"
    if images_dir.is_dir():
        found = _images_in(images_dir)
        if found:
            return found
    found: list[Path] = []
    for key in SPLIT_KEYS:
        entry = data.get(key)
        if not isinstance(entry, str):
            continue
        path = Path(entry)
        path = path if path.is_absolute() else root / path
        if path.is_dir():
            found.extend(_images_in(path))
        elif path.suffix.lower() == ".txt" and path.is_file():
            found.extend(_images_from_list(path, root))
    if found:
        return sorted(set(found))
    return _images_in(root)


def _label_file(image: Path, root: Path) -> Path | None:
    """Label-filen som hör till bilden.

    Appens layout har labels/ bredvid images/, ett delat dataset har
    train/labels/ bredvid train/images/, och en del exporter lägger .txt
    intill bilden. Första träffen vinner.
    """
    candidates = (
        root / "labels" / f"{image.stem}.txt",
        image.parent.parent / "labels" / f"{image.stem}.txt",
        image.parent / f"{image.stem}.txt",
    )
    return next((path for path in candidates if path.is_file()), None)


def _metadata_entries(root: Path) -> dict[str, dict]:
    """Bildposterna i exportens dataset.json, nycklade på filnamn.

    Filen är appens egen metadata och finns bara i en export gjord av appen.
    Saknas den importeras datasetet ändå, men utan bildpar och fångsttider.
    """
    try:
        payload = json.loads((root / METADATA_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    images = payload.get("images") if isinstance(payload, dict) else None
    if not isinstance(images, list):
        return {}
    return {
        image["file_name"]: image
        for image in images
        if isinstance(image, dict) and isinstance(image.get("file_name"), str)
    }


def _captured(path: Path) -> str:
    """Fångsttiden för en bild utan metadata: filens ändringstid."""
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return datetime.now(UTC).isoformat()
    return datetime.fromtimestamp(stamp, UTC).isoformat()


def _rows(
    label: Path | None,
    names: list[str],
    index_of: dict[str, int],
) -> list[tuple[int, float, float, float, float]]:
    """Label-raderna med klassindex i appens klasslista.

    En rad vars klass saknas i data.yaml hoppas över, eftersom indexet då inte
    betyder något. En bild utan label-fil blir ett negativt exempel.
    """
    if label is None:
        return []
    rows = []
    for index, cx, cy, w, h in read_labels(label):
        if not 0 <= index < len(names):
            continue
        rows.append((index_of[names[index]], cx, cy, w, h))
    return rows


def _synthetic(entry: dict, id_offset: int) -> dict:
    """Den syntetiska bildens ursprung och variation, med id:t flyttat.

    source pekar på originalets bild-id, så det flyttas med samma förskjutning
    som bilderna när importen utökar ett befintligt dataset.
    """
    if not entry.get("synthetic"):
        return {}
    fields: dict = {"synthetic": True}
    if isinstance(entry.get("source"), int):
        fields["source"] = entry["source"] + id_offset
    if entry.get("variation") is not None:
        fields["variation"] = entry["variation"]
    return fields


def _file_name(source: Path, image_id: int, used: set[str], rename: bool) -> str:
    """Filnamnet i appens images/.

    Vid ersättning behåller bilden sitt namn, så en återställd export ser ut
    som datasetet gjorde före exporten. Vid utökning döps bilden om till
    appens eget mönster, så den aldrig skriver över en befintlig fil.
    """
    if not rename and source.name not in used:
        return source.name
    suffix = source.suffix.lower() or ".png"
    name = f"img_{image_id:06d}{suffix}"
    counter = 2
    while name in used:
        name = f"img_{image_id:06d}_{counter}{suffix}"
        counter += 1
    return name


def import_yolo(
    store: DatasetStore,
    data_yaml: Path,
    mode: str = MODE_REPLACE,
) -> ImportResult:
    """Importerar ett YOLO-dataset till appens dataset (TASK-159).

    mode avgör om appens befintliga bilder ersätts eller behålls. Vid utökning
    får de importerade bilderna nya id och grupper, och klassnamn som saknas
    läggs sist i klasslistan så att de befintliga annoteringarna behåller sina
    index. Allt läses och kontrolleras innan något skrivs, så ett trasigt
    dataset inte hinner tömma det befintliga.
    """
    if mode not in MODES:
        raise ValueError(f"okänt läge: {mode}")
    data_yaml = Path(data_yaml)
    root = data_yaml.parent
    data = read_data(data_yaml)
    names = read_classes(data_yaml)
    if not names:
        raise ValueError("data.yaml saknar klasslista")
    sources = _image_files(root, data)
    if not sources:
        raise ValueError("hittade inga bilder i datasetet")

    entries = _metadata_entries(root)
    existing = store.metadata_document()["images"]
    if mode == MODE_REPLACE:
        classes = list(names)
        id_offset = 0
        group_offset = 0
        used_names: set[str] = set()
        rename = False
    else:
        classes = store.classes()
        for name in names:
            if name not in classes:
                classes.append(name)
        id_offset = max((image["id"] for image in existing), default=0)
        group_offset = max((image.get("group") or 0 for image in existing), default=0)
        used_names = {image["file_name"] for image in existing}
        rename = True
    index_of = {name: index for index, name in enumerate(classes)}

    planned: list[dict] = []
    skipped = 0
    for source in sources:
        frame = cv2.imread(str(source))
        if frame is None:
            skipped += 1
            continue
        height, width = frame.shape[:2]
        entry = entries.get(source.name, {})
        planned.append(
            {
                "source": source,
                "entry": entry,
                "width": int(entry.get("width") or width),
                "height": int(entry.get("height") or height),
                "rows": _rows(_label_file(source, root), names, index_of),
            }
        )
    if not planned:
        raise ValueError("inga av bilderna i datasetet gick att läsa")

    next_id = (
        max(
            (int(entry["id"]) + id_offset for entry in entries.values() if "id" in entry),
            default=id_offset,
        )
        + 1
    )
    next_group = (
        max(
            (
                int(entry["group"]) + group_offset
                for entry in entries.values()
                if entry.get("group")
            ),
            default=group_offset,
        )
        + 1
    )

    if mode == MODE_REPLACE:
        store.clear()
    store.images_dir.mkdir(parents=True, exist_ok=True)
    imported: list[dict] = []
    for item in planned:
        entry = item["entry"]
        if "id" in entry:
            image_id = int(entry["id"]) + id_offset
        else:
            image_id = next_id
            next_id += 1
        if entry.get("group"):
            group = int(entry["group"]) + group_offset
        else:
            group = next_group
            next_group += 1
        file_name = _file_name(item["source"], image_id, used_names, rename)
        used_names.add(file_name)
        write_labels(store.labels_dir / label_name(file_name), item["rows"])
        shutil.copy2(item["source"], store.images_dir / file_name)
        imported.append(
            {
                "id": image_id,
                "file_name": file_name,
                "width": item["width"],
                "height": item["height"],
                "group": group,
                "captured": entry.get("captured") or _captured(item["source"]),
                **_synthetic(entry, id_offset),
            }
        )

    write_data_yaml(store.data_yaml, classes)
    store.replace_images(imported if mode == MODE_REPLACE else [*existing, *imported])
    return ImportResult(
        images=len(imported),
        pairs=len({image["group"] for image in imported}),
        skipped=skipped,
    )
