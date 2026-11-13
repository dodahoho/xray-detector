"""YOLO-formatet som datasetets interna lagring (TASK-78).

Datasetet ligger som ett vanligt YOLO-dataset: bilderna i images/, en
label-fil per bild i labels/ och klasserna i data.yaml. Formatet läses
direkt av ultralytics och rfdetr, så ingen konvertering behövs före träning.

En label-rad är ``<klassindex> <cx> <cy> <w> <h>`` med måtten normaliserade
mot bildens bredd och höjd. Klassindexet är klassens plats i data.yaml:s
names-lista, så listan och label-filerna måste ändras tillsammans.
"""

import ast
import json
from pathlib import Path

DATA_YAML = "data.yaml"


def read_classes(path: Path) -> list[str]:
    """Klassnamnen ur data.yaml:s names-lista.

    Både listformen (``names: ['a', 'b']``) och dictformen
    (``names: {0: 'a', 1: 'b'}``, som ultralytics skriver) läses, så en fil
    som verktyget har skrivit om går att läsa tillbaka.
    """
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for index, line in enumerate(lines):
        if not line.startswith("names:"):
            continue
        raw = line.removeprefix("names:").strip()
        if raw:
            return _parse_names(raw)
        return _parse_indented_names(lines[index + 1 :])
    return []


def _parse_names(raw: str) -> list[str]:
    try:
        names = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names)]
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    return []


def _parse_indented_names(lines: list[str]) -> list[str]:
    """Dictformen över flera rader: names:\\n  0: a\\n  1: b."""
    names: dict[int, str] = {}
    for line in lines:
        if not line.strip() or not line.startswith((" ", "\t")):
            break
        key, _, value = line.strip().partition(":")
        try:
            names[int(key)] = value.strip().strip("'\"")
        except ValueError:
            break
    return [names[key] for key in sorted(names)]


def write_data_yaml(
    path: Path,
    names: list[str],
    train: str = "images",
    val: str = "images",
) -> None:
    """Skriver data.yaml med klasslistan.

    train och val pekar som default på datasetets egna bilder, så katalogen
    går att träna direkt på. Appens egen träning använder den exporterade
    delningen i stället, där val är en egen delmängd.

    Klassnamnen skrivs som en JSON-lista, som är giltig YAML, så ett namn med
    apostrof eller citattecken inte bryter filen.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"path: {path.parent}",
                f"train: {train}",
                f"val: {val}",
                f"nc: {len(names)}",
                f"names: {json.dumps(names, ensure_ascii=False)}",
            ]
        ),
        encoding="utf-8",
    )


def label_name(file_name: str) -> str:
    """Label-filen som hör till en bild: samma stam med .txt."""
    return f"{Path(file_name).stem}.txt"


def read_labels(path: Path) -> list[tuple[int, float, float, float, float]]:
    """YOLO-raderna som (klassindex, cx, cy, w, h) med normaliserade mått."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            rows.append((int(parts[0]), *(float(value) for value in parts[1:5])))
        except ValueError:
            continue
    return rows


def write_labels(
    path: Path,
    rows: list[tuple[int, float, float, float, float]],
) -> None:
    """Skriver label-filen; en rad per objekt och tom fil för negativa exempel."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            f"{index} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
            for index, cx, cy, w, h in rows
        ),
        encoding="utf-8",
    )


def from_pixels(
    index: int,
    bbox: list[float],
    width: int,
    height: int,
) -> tuple[int, float, float, float, float]:
    """Pixel-bbox (x, y, w, h) till en normaliserad YOLO-rad."""
    x, y, w, h = bbox
    return (index, (x + w / 2) / width, (y + h / 2) / height, w / width, h / height)


def to_pixels(
    row: tuple[int, float, float, float, float],
    width: int,
    height: int,
) -> list[float]:
    """En YOLO-rad till pixel-bbox (x, y, w, h) för bildens storlek."""
    _index, cx, cy, w, h = row
    box_width = w * width
    box_height = h * height
    return [
        cx * width - box_width / 2,
        cy * height - box_height / 2,
        box_width,
        box_height,
    ]
