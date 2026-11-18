import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

from xray_detector.domain.dataset import group_images
from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.infrastructure.dataset_store.yolo import label_name, write_data_yaml

SPLIT_RATIO = 0.8
SPLIT_SEED = 42
#: RF-DETR:s test-del får en egen grupp först när datasetet har minst tre (TASK-93).
MIN_GROUPS_FOR_TEST = 3


def _signature(images: list[dict]) -> frozenset[str]:
    """Klassuppsättningen i en fångstgrupp (TASK-94).

    Räknas på ursprungsbilderna: en variation kan tappa en annotering som hamnat
    utanför bilden, och då ska den inte styra stratifieringen (TASK-111).
    """
    originals = [image for image in images if not image.get("synthetic")]
    return frozenset(
        annotation["class_name"]
        for image in originals or images
        for annotation in image.get("annotations") or []
    )


def _class_group_counts(groups: dict[object, list[dict]]) -> dict[str, int]:
    """Antal fångstgrupper som innehåller respektive klass."""
    counts: dict[str, int] = {}
    for images in groups.values():
        for name in _signature(images):
            counts[name] = counts.get(name, 0) + 1
    return counts


def _rarity_key(images: list[dict], counts: dict[str, int]) -> tuple:
    """Sorteringsnyckel: grupper med den ovanligaste klassen först.

    En klass som bara finns i två grupper får då sina grupper först i kön och
    hinner fördelas på båda delmängderna innan de vanliga klasserna tar plats.
    Negativa exempel saknar klass och läggs sist: de påverkar inte vilka
    klasser som finns i train och val.
    """
    signature = _signature(images)
    if not signature:
        return (1, 0, 0, ())
    return (
        0,
        min(counts[name] for name in signature),
        len(signature),
        tuple(sorted(signature)),
    )


def _stratified_order(groups: dict[object, list[dict]], seed: int) -> list[object]:
    """Gruppnycklarna i stratifierad ordning: ovanligast klass först.

    Ordningen inom samma ovanlighet är seedad, så delningen är reproducerbar.
    """
    counts = _class_group_counts(groups)
    by_rarity: dict[tuple, list[object]] = {}
    for key, images in groups.items():
        by_rarity.setdefault(_rarity_key(images, counts), []).append(key)
    rng = random.Random(seed)
    order: list[object] = []
    for rarity in sorted(by_rarity):
        keys = sorted(by_rarity[rarity], key=str)
        rng.shuffle(keys)
        order.extend(keys)
    return order


def _next_split(assigned: dict[str, list[object]], targets: dict[str, int]) -> str:
    """Delen som ligger längst efter sin andel och fortfarande har plats kvar."""
    open_splits = [
        name for name, target in targets.items() if len(assigned[name]) < target
    ]
    if not open_splits:
        return next(iter(targets))
    return min(
        open_splits,
        key=lambda name: (len(assigned[name]) / targets[name], list(targets).index(name)),
    )


def _assign(
    order: list[object], targets: dict[str, int]
) -> dict[str, list[object]]:
    """Fördelar grupperna så att varje del får sitt målantal.

    Varje grupp går till den del som ligger längst efter sin andel. En klass
    som bara finns i två grupper hamnar därför i både train och val i stället
    för att hamna helt utanför val.
    """
    assigned: dict[str, list[object]] = {name: [] for name in targets}
    for key in order:
        assigned[_next_split(assigned, targets)].append(key)
    return assigned


def _two_way_targets(total: int, ratio: float) -> dict[str, int]:
    """Antal grupper i train respektive val; summan är alltid total."""
    cutoff = round(total * ratio)
    if total and cutoff == 0:
        cutoff = 1
    return {"train": cutoff, "val": total - cutoff}


def _three_way_targets(total: int, ratio: float) -> dict[str, int]:
    """Antal grupper i train, valid och test (TASK-93).

    Train får andelen ratio, resten delas mellan valid och test. Med minst tre
    grupper lämnas alltid en grupp till valid och en till test, så test aldrig
    blir en kopia av valid.
    """
    if total <= 0:
        return {"train": 0, "valid": 0, "test": 0}
    train = round(total * ratio)
    if total >= MIN_GROUPS_FOR_TEST:
        train = max(1, min(train, total - 2))
    elif total >= 2:
        train = max(1, min(train, total - 1))
    else:
        train = 1
    rest = total - train
    valid = (rest + 1) // 2
    return {"train": train, "valid": valid, "test": rest - valid}


def _split(
    images: list[dict], targets: dict[str, int], seed: int
) -> dict[str, list[dict]]:
    groups = group_images(images)
    order = _stratified_order(groups, seed)
    assigned = _assign(order, targets)
    return {
        name: [image for key in keys for image in groups[key]]
        for name, keys in assigned.items()
    }


def train_val_split(
    images: list[dict],
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> tuple[list[dict], list[dict]]:
    """Delar upp bilderna i train/val grupperat på fångstgrupp.

    Bilder med samma "group"-id (samma fångstögonblick) hamnar alltid i
    samma delmängd så att vänster- och högerbild från samma scen inte läcker
    mellan train och val. Delningen är stratifierad på klassuppsättning och
    seedad, så en ovanlig klass hamnar i båda delmängderna och samma seed ger
    samma delning (TASK-94).
    """
    splits = _split(images, _two_way_targets(group_count(images), ratio), seed)
    return splits["train"], splits["val"]


def train_val_test_split(
    images: list[dict],
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> dict[str, list[dict]]:
    """Delar upp bilderna i train/valid/test för RF-DETR (TASK-93).

    Delningen sker per fångstgrupp och stratifieras som train_val_split, så
    test innehåller bilder som inte finns i train eller valid. Test får en egen
    grupp först när datasetet har minst tre grupper; med färre går det inte att
    fylla tre delmängder och test blir tom.
    """
    targets = _three_way_targets(group_count(images), ratio)
    return _split(images, targets, seed)


def group_count(images: list[dict]) -> int:
    """Antal fångstgrupper (bildpar) i en lista bilder (TASK-72).

    En syntetisk bild räknas i sin ursprungsbilds grupp, så siffran är antalet
    ursprungspar och inte antalet kort i datasetvyn (TASK-111).
    """
    return len(group_images(images))


def _fresh_dir(path: Path) -> Path:
    """Tömmer exportkatalogen så bilder från en tidigare export inte ligger kvar."""
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_yolo(store: DatasetStore, export_root: Path, ratio: float = SPLIT_RATIO) -> Path:
    """Kopierar datasetet som ett YOLO-dataset med train/val-delning.

    Datasetet lagras redan i YOLO-format, så exporten kopierar bilder och
    label-filer och skriver en data.yaml för delningen (TASK-78). Returnerar
    sökvägen till data.yaml, så anroparen slipper bygga layouten själv
    (TASK-146).
    """
    dataset = store.load_dataset()
    out_dir = _fresh_dir(export_root / "yolo")
    train_images, val_images = train_val_split(dataset["images"], ratio)

    for split, images in (("train", train_images), ("val", val_images)):
        images_dir = out_dir / "images" / split
        labels_dir = out_dir / "labels" / split
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(
                store.images_dir / image["file_name"],
                images_dir / image["file_name"],
            )
            name = label_name(image["file_name"])
            source = store.labels_dir / name
            if source.exists():
                shutil.copy2(source, labels_dir / name)
            else:
                # YOLO kräver en label-fil även för negativa exempel
                (labels_dir / name).write_text("", encoding="utf-8")

    # Tom val-uppsättning (enda gruppen): låt val peka på train så att
    # ultralytics kan starta, men notera det i manifestet.
    val_relative = "images/val" if val_images else "images/train"
    write_data_yaml(
        out_dir / "data.yaml", dataset["classes"], "images/train", val_relative
    )
    write_manifest(
        out_dir,
        dataset,
        "yolo",
        num_train=len(train_images),
        num_val=len(val_images),
    )
    return out_dir / "data.yaml"


def export_coco(store: DatasetStore, export_root: Path) -> Path:
    """Exporterar datasetet som ett COCO-dataset för verktyg som kräver det."""
    dataset = store.load_dataset()
    out_dir = _fresh_dir(export_root / "coco")
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    for image in dataset["images"]:
        shutil.copy2(
            store.images_dir / image["file_name"],
            out_dir / "images" / image["file_name"],
        )
    atomic_write_json(out_dir / "dataset.json", _coco_document(dataset, dataset["images"]))
    write_manifest(out_dir, dataset, "coco")
    return out_dir


def write_manifest(out_dir: Path, dataset: dict, export_format: str, **extra) -> None:
    manifest = {
        "format": export_format,
        "date": datetime.now(UTC).isoformat(),
        "num_images": len(dataset["images"]),
        "num_objects": sum(len(image["annotations"]) for image in dataset["images"]),
        **extra,
    }
    atomic_write_json(out_dir / "manifest.json", manifest)


def _coco_document(dataset: dict, images: list[dict]) -> dict:
    """COCO-dokument för en delmängd bilder (export till COCO och RF-DETR).

    YOLO:s klassindex blir COCO:s category_id med ett tillagt ett, eftersom
    COCO numrerar kategorierna från 1.
    """
    names = dataset["classes"]
    category_of = {name: index + 1 for index, name in enumerate(names)}
    coco_images = []
    annotations = []
    annotation_id = 1
    for image in images:
        coco_images.append(
            {
                "id": image["id"],
                "file_name": image["file_name"],
                "width": image["width"],
                "height": image["height"],
            }
        )
        for annotation in image["annotations"]:
            category_id = category_of.get(annotation["class_name"])
            if category_id is None:
                continue
            bbox = [round(value, 2) for value in annotation["bbox"]]
            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image["id"],
                    "category_id": category_id,
                    "bbox": bbox,
                    # COCO kräver area och iscrowd; rfdetr läser area rakt av
                    # och faller annars på KeyError (TASK-107)
                    "area": round(bbox[2] * bbox[3], 2),
                    "iscrowd": 0,
                }
            )
            annotation_id += 1
    return {
        "info": dict(dataset["info"]),
        "licenses": [],
        "categories": [
            {"id": index + 1, "name": name} for index, name in enumerate(names)
        ],
        "images": coco_images,
        "annotations": annotations,
    }


def export_rfdetr(
    store: DatasetStore,
    export_root: Path,
    ratio: float = SPLIT_RATIO,
    seed: int = SPLIT_SEED,
) -> Path:
    """Exporterar i RF-DETR:s förväntade format: train/valid/test med _annotations.coco.json.

    Test är en egen delmängd, inte en kopia av valid (TASK-93): ett mått som
    rapporteras på test ska inte vara samma bilder som valet av bästa modell
    gjordes på.
    """
    dataset = store.load_dataset()
    out_dir = _fresh_dir(export_root / "rfdetr")
    splits = train_val_test_split(dataset["images"], ratio, seed)

    for split, images in splits.items():
        split_dir = out_dir / split
        (split_dir / "images").mkdir(parents=True, exist_ok=True)
        for image in images:
            shutil.copy2(
                store.images_dir / image["file_name"],
                split_dir / "images" / image["file_name"],
            )
        split_coco = _coco_document(dataset, images)
        for image in split_coco["images"]:
            image["file_name"] = f"images/{image['file_name']}"
        atomic_write_json(split_dir / "_annotations.coco.json", split_coco)

    write_manifest(
        out_dir,
        dataset,
        "rfdetr",
        num_train=len(splits["train"]),
        num_val=len(splits["valid"]),
        num_test=len(splits["test"]),
    )
    return out_dir
