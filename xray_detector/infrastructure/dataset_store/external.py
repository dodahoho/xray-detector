"""Ett YOLO-dataset på disk, läst för utvärdering (TASK-158).

Utvärderingen kan köras mot ett dataset utanför appen, så länge det ligger i
YOLO-format: ``data.yaml`` med klasserna, ``images/`` med bilderna och
``labels/`` med en label-fil per bild. Modulen bygger samma läsmodell som
DatasetStore ger, så utvärderingen slipper känna till var datasetet kommer
ifrån.

Bilderna får var sin fångstgrupp. Ett dataset utanför appen har inga
fångstpar, och då finns det ingen vy att dela upp mAP på.
"""

from pathlib import Path

import cv2

from xray_detector.infrastructure.dataset_store.yolo import (
    DATA_YAML,
    label_name,
    read_classes,
    read_labels,
    to_pixels,
)

#: Ändelserna en bild läses med, både i en mapp och i ett dataset.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")


def read_dataset(root: Path) -> tuple[dict, Path]:
    """Läser ett YOLO-dataset till (dataset, bildkatalog).

    Klasserna kommer ur data.yaml och annoteringarna ur labels/, omräknade
    till pixel-bboxar med bildens storlek. Saknas data.yaml eller images/ är
    katalogen inget YOLO-dataset, och då säger felet det i stället för att
    utvärderingen tyst räknar på noll bilder.
    """
    root = Path(root)
    data_yaml = root / DATA_YAML
    images_dir = root / "images"
    if not data_yaml.is_file() or not images_dir.is_dir():
        raise ValueError(
            f"{root} är inget YOLO-dataset: data.yaml och images/ saknas"
        )
    names = read_classes(data_yaml)
    labels_dir = root / "labels"
    images = []
    for index, path in enumerate(sorted(images_dir.iterdir()), start=1):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        height, width = frame.shape[:2]
        annotations = [
            {
                "class_name": names[row[0]] if row[0] < len(names) else str(row[0]),
                "bbox": to_pixels(row, width, height),
            }
            for row in read_labels(labels_dir / label_name(path.name))
        ]
        images.append(
            {
                "id": index,
                "file_name": path.name,
                "width": width,
                "height": height,
                "group": index,
                "annotations": annotations,
            }
        )
    return {"classes": names, "images": images}, images_dir
