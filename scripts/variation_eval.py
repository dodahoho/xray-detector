"""Utvärdering av syntetiska bildvariationer på ett litet dataset (TASK-160).

Kör en matris av träningar mot appens eget dataset: en baslinje utan
variationer, varje variationstyp för sig, en kombination av alla fyra och
kombinationen i ökande antal variationer per bildpar. Varje körning mäts mot
samma fasta, manuellt annoterade uppsättning som hålls utanför träningen.

Skriptet ligger utanför applikationslogiken och använder appens egna moduler för
delning, utökning, export, träning och utvärdering. Användarens dataset rörs
aldrig: indata kopieras till en arbetskatalog först, och alla tränade modeller
hamnar där.

Körningarna är dyra, så varje körning sparar sitt resultat i
``runs/<körnings-id>/result.json`` och en omkörning hoppar över det som redan
finns. Använd ``--only`` för att köra om en enskild konfiguration.

    uv run python scripts/variation_eval.py prepare
    uv run python scripts/variation_eval.py run
    uv run python scripts/variation_eval.py report
"""

import argparse
import contextlib
import json
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

from xray_detector.application import evaluation, model_registry
from xray_detector.application.training_history import training_runs
from xray_detector.domain.config import PROJECT_ROOT
from xray_detector.domain.dataset import MODE_ALL, VariationSettings
from xray_detector.infrastructure.dataset_store.export import (
    export_dataset,
    group_count,
    train_val_counts,
    train_val_split,
)
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.infrastructure.training.metrics import (
    Prediction,
    Target,
    match_counts,
)

#: Appens eget dataset, som bara läses.
SOURCE_DATASET = Path.home() / ".xray-detector" / "datasets"
#: Samma delning som appens export använder, så train/val räknas lika.
TRAIN_RATIO = 0.8
EPOCHS = 100
#: Flera frön per konfiguration, eftersom variationerna dras slumpmässigt.
VARIATION_SEEDS = (1, 2, 3)
#: Baslinjen har inga variationer att dra, så den upprepas för att visa att
#: träningen är deterministisk.
BASELINE_REPEATS = 2
RESULTS_NAME = "results.json"
CHART_DIR = Path("docs/rapporter/bilder")


@dataclass(frozen=True)
class BaseModel:
    """Basmodellen och de träningsparametrar som hör till den.

    Arbetskatalogerna ligger utanför repot, så inga tränade modeller hamnar i
    git. Den kompletterande katalogen hör till matrisen med
    överträningsvakten avstängd: vakten stoppar alla körningar på det här
    datasetet innan modellen hunnit lära sig något, så utan den går
    variationernas effekt inte att mäta.
    """

    key: str
    label: str
    family: str
    weights: str
    imgsz: int
    batch: int
    work_root: Path
    supplement_root: Path
    report_path: Path
    chart_prefix: str
    task_id: str
    #: Kontrollkörningar med vakten av för en dyr basmodell, där hela matrisen
    #: utan vakt inte ryms i rimlig tid. None när ingen kontroll görs.
    control_root: Path | None = None


#: Bildstorleken är användarens sparade träningsinställning. Appens uträknade
#: default för 1280x720-bilder är 1280, men den storleken tog 15 gånger längre
#: tid per steg på det här datasetet utan att modellen lärde sig snabbare.
BASES: dict[str, BaseModel] = {
    "yolo": BaseModel(
        key="yolo26m",
        label="YOLO26 medium",
        family="yolo",
        weights="yolo26m.pt",
        imgsz=800,
        batch=8,
        work_root=Path.home() / ".xray-detector" / "eval" / "task-160",
        supplement_root=Path.home() / ".xray-detector" / "eval" / "task-160-noguard",
        report_path=Path("docs/rapporter/bildvariationer.md"),
        chart_prefix="",
        task_id="TASK-160",
    ),
    "rfdetr": BaseModel(
        key="checkpoint-best-total",
        label="RF-DETR large dvxray",
        family="rfdetr",
        weights="checkpoint_best_total.pth",
        imgsz=800,
        batch=8,
        work_root=Path.home() / ".xray-detector" / "eval" / "task-160-rfdetr",
        supplement_root=Path.home() / ".xray-detector" / "eval" / "task-160-rfdetr-noguard",
        report_path=Path("docs/rapporter/bildvariationer-rfdetr.md"),
        chart_prefix="rfdetr-",
        task_id="TASK-161",
        control_root=Path.home() / ".xray-detector" / "eval" / "task-160-rfdetr-kontroll",
    ),
}


@dataclass(frozen=True)
class Config:
    """En punkt i matrisen: etiketten rapporten visar och variationerna."""

    key: str
    label: str
    settings: VariationSettings | None


def _all_types(count: int) -> VariationSettings:
    """Alla fyra variationstyper i samma bild, med dialogens standardstyrka."""
    return VariationSettings(
        count=count,
        mode=MODE_ALL,
        rotation=True,
        rotation_degrees=360.0,
        flip_horizontal=True,
        flip_vertical=True,
        scale=True,
        scale_up_percent=50.0,
        scale_down_percent=50.0,
        color=True,
        color_percent=20.0,
    )


#: Styrkorna är dialogens standardvärden, alltså det en användare får när
#: kryssrutan sätts utan att ändra något.
CONFIGS: tuple[Config, ...] = (
    Config("baseline", "Baslinje (inga variationer)", None),
    Config(
        "rotation",
        "Rotation ±360°",
        VariationSettings(count=1, mode=MODE_ALL, rotation=True, rotation_degrees=360.0),
    ),
    Config(
        "flip",
        "Vändning (båda riktningarna)",
        VariationSettings(count=1, mode=MODE_ALL, flip_horizontal=True, flip_vertical=True),
    ),
    Config(
        "scale",
        "Storlek ±50 %",
        VariationSettings(
            count=1, mode=MODE_ALL, scale=True, scale_up_percent=50.0, scale_down_percent=50.0
        ),
    ),
    Config(
        "color",
        "Färg ±20 %",
        VariationSettings(count=1, mode=MODE_ALL, color=True, color_percent=20.0),
    ),
    Config("all-1", "Alla fyra, 1 variation", _all_types(1)),
    Config("all-2", "Alla fyra, 2 variationer", _all_types(2)),
    Config("all-5", "Alla fyra, 5 variationer", _all_types(5)),
    Config("all-10", "Alla fyra, 10 variationer", _all_types(10)),
    Config("all-20", "Alla fyra, 20 variationer", _all_types(20)),
)
CONFIG_BY_KEY = {config.key: config for config in CONFIGS}
#: Konfigurationerna som hör till jämförelsen av variationstyper.
TYPE_KEYS = ("baseline", "rotation", "flip", "scale", "color", "all-1")
#: Konfigurationerna som hör till kurvan över antal variationer per bildpar.
COUNT_KEYS = ("baseline", "all-1", "all-2", "all-5", "all-10", "all-20")
COUNT_VALUES = {"all-1": 1, "all-2": 2, "all-5": 5, "all-10": 10, "all-20": 20}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _stdev(values: list[float]) -> float:
    """Standardavvikelsen; noll för en enda mätning i stället för ett fel."""
    return statistics.stdev(values) if len(values) > 1 else 0.0


def prepare(work_root: Path, source: Path = SOURCE_DATASET) -> None:
    """Delar appens dataset i en träningsdel och en fast utvärderingsdel.

    Delningen är appens egen (``train_val_split`` med dess seed), så
    utvärderingsdelen är precis de bildpar appen själv skulle lägga i val.
    Utvärderingsdelen kopieras en gång och rörs sedan aldrig: den får inga
    variationer och ingår inte i någon träning.
    """
    dataset = DatasetStore(source).load_dataset()
    train, val = train_val_split(dataset["images"], TRAIN_RATIO)
    train_ids = [image["id"] for image in train]
    val_ids = [image["id"] for image in val]
    if not train_ids or not val_ids:
        raise SystemExit("Datasetet har för få bildpar för att delas")
    for name, drop in (("train_base", val_ids), ("eval_fixed", train_ids)):
        target = work_root / "datasets" / name
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target)
        store = DatasetStore(target)
        store.delete_images(drop)
        pairs, synthetic = store.dataset_counts()
        print(f"{name}: {pairs} bildpar, {synthetic} syntetiska")
    _write_json(
        work_root / "datasets" / "split.json",
        {
            "source": str(source),
            "train_ids": sorted(train_ids),
            "eval_ids": sorted(val_ids),
            "train_pairs": group_count(train),
            "eval_pairs": group_count(val),
            "train_objects": sum(len(image["annotations"]) for image in train),
            "eval_objects": sum(len(image["annotations"]) for image in val),
        },
    )


def _prediction(detections, class_index: dict[str, int]) -> Prediction:
    """Detektionerna som appens Prediction, samma form utvärderingen räknar på."""
    kept = [
        (detection, class_index[detection.class_name])
        for detection in detections
        if detection.class_name in class_index
    ]
    boxes = [[detection.x1, detection.y1, detection.x2, detection.y2] for detection, _ in kept]
    scores = [detection.confidence for detection, _ in kept]
    labels = [index for _, index in kept]
    return Prediction(
        boxes=np.array(boxes, dtype=float).reshape(-1, 4),
        scores=np.array(scores, dtype=float),
        labels=np.array(labels, dtype=int),
    )


def _target(image: dict, class_index: dict[str, int]) -> Target:
    """Bildens annoteringar som appens Target, i xyxy-pixlar."""
    kept = [
        (annotation, class_index[annotation["class_name"]])
        for annotation in image["annotations"]
        if annotation["class_name"] in class_index
    ]
    boxes = [
        [x, y, x + width, y + height]
        for annotation, _ in kept
        for x, y, width, height in [annotation["bbox"]]
    ]
    labels = [index for _, index in kept]
    return Target(
        boxes=np.array(boxes, dtype=float).reshape(-1, 4),
        labels=np.array(labels, dtype=int),
    )


def _detector(run):
    """Detektorn för en tränad körning, med utvärderingens låga tröskel."""
    spec = model_registry.ModelSpec(
        key=f"trained-{run.run_id}",
        label=run.run_id,
        family=run.family,
        weights=str(run.weights),
    )
    return model_registry.create_detector(spec, evaluation.EVAL_CONFIDENCE)


def false_positives_per_image(
    run, dataset: dict, images_dir: Path, threshold: float
) -> float:
    """Falska detektioner per bild vid driftströskeln.

    Appens falsklarm räknas bara på bilder utan objekt, och den fasta
    utvärderingsuppsättningen har inga sådana. Här räknas i stället de
    detektioner som inte matchar något facit, vilket är samma sak sedd från
    andra hållet: larm som inte motsvarar ett objekt.
    """
    detector = _detector(run)
    class_index = {name: index for index, name in enumerate(dataset["classes"])}
    total = 0
    images = 0
    for image in dataset["images"]:
        frame = cv2.imread(str(Path(images_dir) / image["file_name"]))
        if frame is None:
            continue
        prediction = _prediction(detector.detect(frame), class_index)
        target = _target(image, class_index)
        _found, false_positives, _missed = match_counts(prediction, target, threshold)
        total += false_positives
        images += 1
    return total / images if images else 0.0


def _train(run_dir: Path, dataset: Path, label: str, guard: str, base: BaseModel) -> float:
    """Tränar en körning med appens träningsprocess; returnerar körtiden."""
    command = [
        sys.executable,
        "-m",
        "xray_detector.infrastructure.training.train_task",
        "--dataset",
        str(dataset),
        "--weights",
        str(PROJECT_ROOT / "models" / base.weights),
        "--output",
        str(run_dir / "model"),
        "--epochs",
        str(EPOCHS),
        "--imgsz",
        str(base.imgsz),
        "--batch",
        str(base.batch),
        "--family",
        base.family,
        "--overfitting-guard",
        guard,
        "--name",
        label,
        "--base-name",
        base.label,
    ]
    started = time.monotonic()
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    duration = time.monotonic() - started
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout or "").splitlines()[-20:])
        raise RuntimeError(f"Träningen misslyckades (kod {completed.returncode}):\n{tail}")
    return duration


def run_one(
    config: Config,
    seed: int | None,
    run_id: str,
    work_root: Path,
    guard: str,
    base: BaseModel,
) -> dict:
    """Kör en konfiguration: utöka, exportera, träna och utvärdera."""
    run_dir = work_root / "runs" / run_id
    result_path = run_dir / "result.json"
    if result_path.exists():
        print(f"{run_id}: hoppar över, resultatet finns")
        return _read_json(result_path)

    shutil.rmtree(run_dir, ignore_errors=True)
    dataset_dir = run_dir / "dataset"
    shutil.copytree(work_root / "datasets" / "train_base", dataset_dir)
    store = DatasetStore(dataset_dir)
    synthetic = 0
    if config.settings is not None:
        synthetic = store.add_variations(config.settings, seed=seed)
    train_pairs, val_pairs = train_val_counts(store, TRAIN_RATIO, family=base.family)
    dataset = export_dataset(store, run_dir / "export", base.family, TRAIN_RATIO)
    exported = _read_json(run_dir / "export" / base.family / "manifest.json")

    print(
        f"{run_id}: {train_pairs} train-grupper, {val_pairs} val-grupper, "
        f"{exported['num_train']} train-bilder, {synthetic} syntetiska"
    )
    duration = _train(run_dir, dataset, config.label, guard, base)

    runs = training_runs(run_dir / "model")
    if not runs:
        raise RuntimeError(f"{run_id}: träningen skrev inget manifest")
    run = runs[0]
    eval_dataset = DatasetStore(work_root / "datasets" / "eval_fixed").load_dataset()
    report = evaluation.evaluate_run(
        run, eval_dataset, work_root / "datasets" / "eval_fixed" / "images", split="all"
    )
    threshold = float(report["operating_point"]["threshold"])
    result = {
        "run_id": run_id,
        "config": config.key,
        "label": config.label,
        "seed": seed,
        "synthetic_pairs": synthetic,
        "train_pairs": train_pairs,
        "val_pairs": val_pairs,
        "train_images": int(exported["num_train"]),
        "val_images": int(exported["num_val"]),
        "epochs": run.epochs,
        "epochs_completed": run.epochs_completed,
        "stopped_by_guard": run.stop_reason == "overfitting",
        "status": run.status,
        "duration_seconds": round(duration, 1),
        "map50_95": float(report["overall"]["map50_95"]),
        "map50": float(report["overall"]["map50"]),
        "views": {
            view: {
                "map50_95": float(values["map50_95"]),
                "map50": float(values["map50"]),
                "images": int(values["images"]),
            }
            for view, values in (report.get("views") or {}).items()
        },
        "operating_threshold": threshold,
        "recall": float(report["operating_point"]["recall"]),
        "false_alarms_per_image": float(report["false_alarms"]["per_image"]),
        "negative_images": int(report["false_alarms"]["images"]),
        "false_positives_per_image": false_positives_per_image(
            run, eval_dataset, work_root / "datasets" / "eval_fixed" / "images", threshold
        ),
        "eval_images": int(report["images"]),
        "eval_objects": int(report["positives"]),
    }
    _write_json(result_path, result)
    print(
        f"{run_id}: mAP50-95 {result['map50_95']:.3f}  mAP50 {result['map50']:.3f}  "
        f"{result['epochs_completed']}/{result['epochs']} epoker  {duration:.0f} s"
    )
    return result


def run_matrix(
    work_root: Path,
    only: list[str] | None,
    guard: str,
    base: BaseModel,
    seeds: tuple[int, ...] = VARIATION_SEEDS,
) -> None:
    """Kör hela matrisen; ``only`` begränsar den till några konfigurationer."""
    if not (work_root / "datasets" / "train_base").exists():
        raise SystemExit("Kör prepare först")
    results = []
    for config in CONFIGS:
        if only and config.key not in only:
            continue
        if config.settings is None:
            results.extend(
                run_one(config, None, f"{config.key}-r{index}", work_root, guard, base)
                for index in range(1, BASELINE_REPEATS + 1)
            )
            continue
        results.extend(
            run_one(config, seed, f"{config.key}-s{seed}", work_root, guard, base)
            for seed in seeds
        )
    _write_json(
        work_root / RESULTS_NAME,
        {
            "generated": datetime.now(UTC).isoformat(),
            "base_model": base.key,
            "base_label": base.label,
            "family": base.family,
            "epochs": EPOCHS,
            "imgsz": base.imgsz,
            "batch": base.batch,
            "train_ratio": TRAIN_RATIO,
            "overfitting_guard": guard,
            "variation_seeds": list(seeds),
            "runs": results,
        },
    )


def _load_results(work_root: Path, family: str) -> dict:
    """Resultaten ur results.json, eller ur körningarnas egna filer."""
    path = work_root / RESULTS_NAME
    if path.exists():
        payload = _read_json(path)
    else:
        payload = {
            "runs": [
                _read_json(result)
                for result in sorted((work_root / "runs").glob("*/result.json"))
            ]
        }
    payload["runs"] = _with_image_counts(payload["runs"], work_root, family)
    return payload


def _with_image_counts(runs: list[dict], work_root: Path, family: str) -> list[dict]:
    """Antalet train- och valbilder ur exportens manifest.

    Bilderna räknas per bild, inte per fångstgrupp: en grupp bär alla
    variationer av sitt bildpar, så gruppantalet säger inget om hur många
    bilder träningen faktiskt ser.
    """
    for run in runs:
        if "train_images" in run:
            continue
        manifest = work_root / "runs" / run["run_id"] / "export" / family / "manifest.json"
        try:
            exported = _read_json(manifest)
        except (OSError, ValueError):
            continue
        run["train_images"] = int(exported.get("num_train") or 0)
        run["val_images"] = int(exported.get("num_val") or 0)
    return runs


def _by_config(runs: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for run in runs:
        grouped.setdefault(run["config"], []).append(run)
    return grouped


def _summary(runs: list[dict]) -> dict:
    """Medelvärde och spridning för en konfigurations körningar."""
    return {
        "n": len(runs),
        "map50_95": _mean([run["map50_95"] for run in runs]),
        "map50_95_std": _stdev([run["map50_95"] for run in runs]),
        "map50": _mean([run["map50"] for run in runs]),
        "map50_std": _stdev([run["map50"] for run in runs]),
        "epochs": _mean([run["epochs_completed"] for run in runs]),
        "duration": _mean([run["duration_seconds"] for run in runs]),
        "false_positives": _mean([run["false_positives_per_image"] for run in runs]),
        "stopped": sum(1 for run in runs if run["stopped_by_guard"]),
        "train_pairs": runs[0]["train_pairs"],
        "val_pairs": runs[0]["val_pairs"],
        "train_images": runs[0].get("train_images", 0),
        "val_images": runs[0].get("val_images", 0),
        "synthetic_pairs": runs[0]["synthetic_pairs"],
    }


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("|" + "|".join("---" for _ in header) + "|")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _delta(value: float, baseline: float) -> str:
    return f"{value - baseline:+.3f}"


def _charts(
    summaries: dict[str, dict], prefix: str = "", with_epochs: bool = True
) -> dict[str, str]:
    """Graferna rapporten bäddar in; returnerar sökvägarna relativt rapporten."""
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}

    type_keys = [key for key in TYPE_KEYS if key in summaries]
    labels = [CONFIG_BY_KEY[key].label for key in type_keys]
    values = [summaries[key]["map50_95"] for key in type_keys]
    errors = [summaries[key]["map50_95_std"] for key in type_keys]
    figure, axes = plt.subplots(figsize=(8, 4.2))
    colors = ["#8a8a8a"] + ["#2f6fb3"] * (len(type_keys) - 1)
    axes.bar(labels, values, yerr=errors, capsize=4, color=colors)
    axes.axhline(summaries["baseline"]["map50_95"], color="#c0392b", linestyle="--", linewidth=1)
    axes.set_ylabel("mAP50-95 mot fast utvärderingsset")
    axes.set_title("Variationstyper mot baslinjen")
    axes.tick_params(axis="x", rotation=20)
    for tick in axes.get_xticklabels():
        tick.set_horizontalalignment("right")
    figure.tight_layout()
    paths["types"] = CHART_DIR / f"{prefix}variationstyper.png"
    figure.savefig(paths["types"], dpi=150)
    plt.close(figure)

    count_keys = [key for key in COUNT_KEYS if key in summaries]
    counts = [0] + [COUNT_VALUES[key] for key in count_keys if key in COUNT_VALUES]
    means = [summaries["baseline"]["map50_95"]] + [
        summaries[key]["map50_95"] for key in count_keys if key in COUNT_VALUES
    ]
    deviations = [summaries["baseline"]["map50_95_std"]] + [
        summaries[key]["map50_95_std"] for key in count_keys if key in COUNT_VALUES
    ]
    figure, axes = plt.subplots(figsize=(8, 4.2))
    axes.errorbar(counts, means, yerr=deviations, marker="o", capsize=4, color="#2f6fb3")
    axes.set_xlabel("Variationer per bildpar (0 = baslinjen)")
    axes.set_ylabel("mAP50-95 mot fast utvärderingsset")
    axes.set_title("Fler variationer per bildpar")
    axes.set_xticks(counts)
    axes.grid(alpha=0.3)
    figure.tight_layout()
    paths["counts"] = CHART_DIR / f"{prefix}antal-variationer.png"
    figure.savefig(paths["counts"], dpi=150)
    plt.close(figure)

    if not with_epochs:
        return {name: str(path) for name, path in paths.items()}

    figure, axes = plt.subplots(figsize=(8, 4.2))
    epochs = [summaries[key]["epochs"] for key in type_keys]
    axes.bar(labels, epochs, color="#5b8c5a")
    axes.set_ylabel("Genomförda epoker (medel)")
    axes.set_title("När överträningsvakten stoppade träningen")
    axes.tick_params(axis="x", rotation=20)
    for tick in axes.get_xticklabels():
        tick.set_horizontalalignment("right")
    figure.tight_layout()
    paths["epochs"] = CHART_DIR / f"{prefix}epoker.png"
    figure.savefig(paths["epochs"], dpi=150)
    plt.close(figure)
    return {name: str(path) for name, path in paths.items()}


TYPE_HEADER = [
    "Konfiguration",
    "mAP50-95",
    "Δ mot baslinje",
    "mAP50",
    "Falska detektioner/bild",
    "Epoker",
]
COUNT_HEADER = [
    "Konfiguration",
    "Syntetiska par per originalpar",
    "Train-bilder",
    "mAP50-95",
    "Δ mot baslinje",
    "mAP50",
    "Falska detektioner/bild",
    "Epoker",
]
SPREAD_HEADER = ["Konfiguration", "Körningar", "mAP50-95", "Std", "Min–max"]


def _type_rows(summaries: dict[str, dict], baseline: float) -> list[list[str]]:
    """Raderna för jämförelsen av variationstyper."""
    return [
        [
            CONFIG_BY_KEY[key].label,
            f"{summaries[key]['map50_95']:.3f} ± {summaries[key]['map50_95_std']:.3f}",
            _delta(summaries[key]["map50_95"], baseline),
            f"{summaries[key]['map50']:.3f} ± {summaries[key]['map50_std']:.3f}",
            f"{summaries[key]['false_positives']:.2f}",
            f"{summaries[key]['epochs']:.0f}",
        ]
        for key in TYPE_KEYS
        if key in summaries
    ]


def _count_rows(summaries: dict[str, dict], baseline: float) -> list[list[str]]:
    """Raderna för kurvan över antal variationer per bildpar."""
    return [
        [
            CONFIG_BY_KEY[key].label,
            str(summaries[key]["synthetic_pairs"]),
            str(summaries[key]["train_images"]),
            f"{summaries[key]['map50_95']:.3f} ± {summaries[key]['map50_95_std']:.3f}",
            _delta(summaries[key]["map50_95"], baseline),
            f"{summaries[key]['map50']:.3f}",
            f"{summaries[key]['false_positives']:.2f}",
            f"{summaries[key]['epochs']:.0f}",
        ]
        for key in COUNT_KEYS
        if key in summaries
    ]


def _spread_rows(
    summaries: dict[str, dict], grouped: dict[str, list[dict]]
) -> list[list[str]]:
    """Raderna för spridningen mellan upprepningarna."""
    rows = []
    for config in CONFIGS:
        if config.key not in summaries:
            continue
        summary = summaries[config.key]
        values = [run["map50_95"] for run in grouped[config.key]]
        rows.append(
            [
                config.label,
                str(summary["n"]),
                f"{summary['map50_95']:.3f}",
                f"{summary['map50_95_std']:.3f}",
                f"{min(values):.3f}–{max(values):.3f}",
            ]
        )
    return rows


def _view_rows(
    summaries: dict[str, dict], grouped: dict[str, list[dict]], views: list[str]
) -> list[list[str]]:
    """mAP50-95 per vy, medel över upprepningarna."""
    rows = []
    for key in TYPE_KEYS:
        if key not in summaries:
            continue
        values = []
        for view in views:
            numbers = [
                run["views"][view]["map50_95"] for run in grouped[key] if view in run["views"]
            ]
            values.append(f"{_mean(numbers):.3f}")
        rows.append([CONFIG_BY_KEY[key].label, *values])
    return rows


def _ranking_line(summaries: dict[str, dict]) -> str:
    """Rangordningen efter mAP50-95, med baslinjen som jämförelsepunkt."""
    ordered = sorted(
        (key for key in TYPE_KEYS if key in summaries),
        key=lambda key: summaries[key]["map50_95"],
        reverse=True,
    )
    parts = [
        f"{CONFIG_BY_KEY[key].label} {summaries[key]['map50_95']:.3f}" for key in ordered
    ]
    return "Rangordning efter mAP50-95: " + " > ".join(parts) + "."


def _views(runs: list[dict]) -> list[str]:
    return sorted({view for run in runs for view in run["views"]})


def _run_rows(grouped: dict[str, list[dict]]) -> list[list[str]]:
    """En rad per körning: bildpar, epoker, om vakten stoppade den och körtid."""
    return [
        [
            run["run_id"],
            f"{run['train_pairs']}/{run.get('train_images', 0)}",
            f"{run['val_pairs']}/{run.get('val_images', 0)}",
            str(run["synthetic_pairs"]),
            f"{run['epochs_completed']}/{run['epochs']}",
            "ja" if run["stopped_by_guard"] else "nej",
            f"{run['duration_seconds']:.0f} s",
        ]
        for config in CONFIGS
        for run in sorted(grouped.get(config.key, []), key=lambda item: item["run_id"])
    ]


RUN_HEADER = [
    "Körning",
    "Train (par/bilder)",
    "Val (par/bilder)",
    "Syntetiska par",
    "Epoker",
    "Stoppad av vakten",
    "Körtid",
]


def _display_path(path: Path) -> str:
    """Sökvägen med hemkatalogen som `~` och snedstreck, så den går att läsa."""
    try:
        return "~/" + Path(path).relative_to(Path.home()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _chart_link(path: Path, report_path: Path, caption: str) -> str:
    """Bildlänken med snedstreck, så markdown läser sökvägen på alla plattformar."""
    return f"![{caption}]({Path(path).relative_to(report_path.parent).as_posix()})"


def report(base: BaseModel) -> None:
    """Skriver markdown-rapporten ur resultaten."""
    work_root = base.work_root
    report_path = base.report_path
    supplement_root = base.supplement_root
    payload = _load_results(work_root, base.family)
    runs = payload["runs"]
    if not runs:
        raise SystemExit("Inga resultat att rapportera")
    grouped = _by_config(runs)
    summaries = {key: _summary(value) for key, value in grouped.items()}
    split = _read_json(work_root / "datasets" / "split.json")
    charts = _charts(summaries, base.chart_prefix)
    baseline = summaries["baseline"]["map50_95"]
    supplement = None
    supplement_payload = _load_results(supplement_root, base.family)
    if supplement_payload["runs"]:
        supplement_grouped = _by_config(supplement_payload["runs"])
        supplement = {
            "payload": supplement_payload,
            "grouped": supplement_grouped,
            "summaries": {key: _summary(value) for key, value in supplement_grouped.items()},
            "charts": _charts(
                {key: _summary(value) for key, value in supplement_grouped.items()},
                f"{base.chart_prefix}utan-vakt-",
                with_epochs=False,
            ),
        }
    lines = []
    add = lines.append

    add("# Syntetiska bildvariationer vid ett tiotal annoterade bildpar")
    add("")
    add(
        f"**Uppgift:** {base.task_id} · **Basmodell:** {base.label} (`{base.weights}`) · "
        f"**Epoker:** {payload.get('epochs', EPOCHS)} · **Bildstorlek:** "
        f"{payload.get('imgsz', base.imgsz)} · **Batch:** {payload.get('batch', base.batch)}"
    )
    add("")
    add(
        "Rapporten mäter hur detektionsprestandan påverkas när datasetet utökas med "
        "syntetiska bildvariationer. Alla körningar utgår från samma basmodell, samma "
        "epokantal, bildstorlek och batch, och utvärderas mot samma fasta uppsättning "
        "manuellt annoterade bildpar som aldrig ingår i träningen och aldrig utökas."
    )
    add("")

    add("## Sammanfattning")
    add("")
    add(_summary_bullets(summaries, baseline, supplement))
    add("")

    add("## Metod")
    add("")
    add("### Dataset och fast utvärderingsuppsättning")
    add("")
    add(
        f"Appens dataset innehåller {split['train_pairs'] + split['eval_pairs']} manuellt "
        f"annoterade bildpar ({split['train_objects'] + split['eval_objects']} objekt) och "
        "inga syntetiska bilder. Delningen är appens egen (`train_val_split` med seed 42 och "
        f"{int(TRAIN_RATIO * 100)} % till train):"
    )
    add("")
    add(
        _table(
            ["Del", "Bildpar", "Bilder", "Objekt", "Används till"],
            [
                [
                    "train_base",
                    str(split["train_pairs"]),
                    str(split["train_pairs"] * 2),
                    str(split["train_objects"]),
                    "Träning, med eller utan variationer",
                ],
                [
                    "eval_fixed",
                    str(split["eval_pairs"]),
                    str(split["eval_pairs"] * 2),
                    str(split["eval_objects"]),
                    "Utvärdering, aldrig utökad",
                ],
            ],
        )
    )
    add("")
    export_name = "export_yolo" if base.family == "yolo" else "export_rfdetr"
    splits = "train och val" if base.family == "yolo" else "train, valid och test"
    add(
        f"Träningsdelen exporteras med appens `{export_name}`, som delar den i {splits} "
        "per bildpar. Variationerna läggs till före exporten, så alla variationer av ett "
        "bildpar hamnar i samma delmängd och aldrig läcker mellan delmängderna. "
        "Utvärderingsdelen kopieras en gång i `prepare` och rörs sedan aldrig."
    )
    add("")
    add("### Variationerna")
    add("")
    add(
        "Styrkorna är dialogens standardvärden, alltså det en användare får när kryssrutan "
        "sätts utan att ändra något. Varje konfiguration körs med tre olika frön, eftersom "
        "`DatasetStore.add_variations` drar variationerna slumpmässigt. Appens datasetvy "
        "skickar ingen seed, så tre frön motsvarar tre olika klick på Utöka."
    )
    add("")
    add(
        _table(
            ["Konfiguration", "Typ", "Antal per bildpar", "Läge"],
            [
                ["Baslinje", "–", "0", "–"],
                ["Rotation", "rotation ±360°", "1", "Alla valda variationer"],
                ["Vändning", "horisontell + vertikal", "1", "Alla valda variationer"],
                ["Storlek", "±50 %", "1", "Alla valda variationer"],
                ["Färg", "kontrast och ljusstyrka ±20 %", "1", "Alla valda variationer"],
                ["Alla fyra", "alla fyra typerna", "1, 2, 5, 10, 20", "Alla valda variationer"],
            ],
        )
    )
    add("")
    add("### Träningen")
    add("")
    guard_text = (
        "ultralytics egen early stopping (patience 10)"
        if base.family == "yolo"
        else "rfdetr-paketets egen early stopping (patience 10)"
    )
    add(
        f"Träningen körs med appens `train_task` i en egen process, precis som träningsvyn "
        f"startar den: {base.label} som bas, {payload.get('epochs', EPOCHS)} epoker som "
        f"tak, bildstorlek {payload.get('imgsz', base.imgsz)} och batch "
        f"{payload.get('batch', base.batch)}. "
        f"Överträningsvakten är på, så {guard_text} kan avsluta körningen i förtid. "
        "Antalet genomförda epoker redovisas per körning."
    )
    add("")
    if supplement is not None:
        add(
            "Vakten visade sig avgöra hela resultatet på det här datasetet, så matrisen "
            "kördes en gång till med vakten avstängd. Den kompletterande matrisen står under "
            "**Kompletterande matris utan överträningsvakt** och är den som svarar på vilka "
            "variationer som hjälper; den första matrisen visar vad appens "
            "standardinställning gör med samma data."
        )
        add("")
    elif base.control_root is not None:
        add(
            "Hela matrisen utan vakt ryms inte i rimlig tid med den här basmodellen, så i "
            "stället kördes en kontroll med bara de konfigurationer som behövs för att "
            "avgöra om vakten orsakar resultaten. Den står under **Kontroll med "
            "överträningsvakten av**."
        )
        add("")
    if base.family != "yolo":
        add(
            "RF-DETR-exporten har också en test-del som träningen inte använder. "
            "Utvärderingen sker mot `eval_fixed`, inte mot exportens valid eller test, så "
            "den del som styr early stopping är inte samma bilder som mätningen görs på."
        )
        add("")
    add("### Mätningen")
    add("")
    add(
        "Varje tränad modell utvärderas med appens `evaluate_run` mot `eval_fixed` med "
        "split `all`, alltså alla fyra bilderna. mAP räknas över hela "
        "precision/recall-kurvan vid konfidenströskel 0,01, och driftläget är den tröskel "
        "som ger 95 % recall. Per vy delas bilderna efter sin plats i bildparet, samma "
        "uppdelning som utvärderingsvyn visar."
    )
    add("")
    add(
        "Appens `falsklarm per bild` räknas bara på bilder utan objekt. Den fasta "
        "utvärderingsuppsättningen har inga sådana, så det måttet är alltid noll och "
        "redovisas som det är. Som komplement räknas **falska detektioner per bild**: de "
        "detektioner vid driftströskeln som inte matchar något facit, alltså larm som inte "
        "motsvarar ett objekt."
    )
    add("")

    add("## Resultat med överträningsvakten på")
    add("")
    add("### Körningarna")
    add("")
    add(_table(RUN_HEADER, _run_rows(grouped)))
    add("")
    add(
        "Train- och val-bilderna är de appens export gav efter utökningen. Val-bilderna är "
        "träningens egen valdel och används bara för early stopping och val av bästa "
        "checkpoint; mätningen sker mot `eval_fixed`."
    )
    add("")
    add("### Variationstyper mot baslinjen")
    add("")
    add(_chart_link(charts["types"], report_path, "Variationstyper mot baslinjen"))
    add("")
    add(_table(TYPE_HEADER, _type_rows(summaries, baseline)))
    add("")
    add(_ranking_line(summaries))
    add("")
    add("Per vy, mAP50-95 (medel över upprepningarna):")
    add("")
    add(_table(["Konfiguration", *_views(runs)], _view_rows(summaries, grouped, _views(runs))))
    add("")
    add("### Kombination och antal variationer per bildpar")
    add("")
    add(_chart_link(charts["counts"], report_path, "Antal variationer per bildpar"))
    add("")
    add(_table(COUNT_HEADER, _count_rows(summaries, baseline)))
    add("")
    add("### Spridning mellan upprepningar")
    add("")
    baseline_std = summaries["baseline"]["map50_95_std"]
    if baseline_std == 0:
        spread_text = (
            "Baslinjen har inga variationer att dra, så dess två körningar är identiska: "
            "träningen är deterministisk (seed 42, `deterministic=True`). Spridningen i "
            "tabellen nedan kommer därför enbart från att variationerna dras olika, och den "
            "anger hur stor en skillnad mellan två konfigurationer måste vara för att inte "
            "vara slump."
        )
    else:
        spread_text = (
            f"Baslinjen har inga variationer att dra, men dess två körningar skiljer sig ändå "
            f"({baseline_std:.3f} i standardavvikelse): träningen är alltså inte deterministisk "
            "för den här basmodellen. Spridningen i tabellen nedan är därför en undre gräns "
            "för hur stor en skillnad mellan två konfigurationer måste vara för att betyda "
            "något."
        )
    add(spread_text)
    add("")
    add(_table(SPREAD_HEADER, _spread_rows(summaries, grouped)))
    add("")
    add("### När överträningsvakten stoppade träningen")
    add("")
    add(_chart_link(charts["epochs"], report_path, "Epoker per konfiguration"))
    add("")
    add(
        "Vakten stoppade varje körning i den här matrisen. Antalet epoker skiljer sig "
        "eftersom early stopping bryter när valvärdet stått still i tio epoker, och det "
        "inträffar tidigare när datasetet är litet: med tolv träningsbilder och batch 8 är "
        "en epok bara två optimeringssteg, så tio epoker utan förbättring är tjugo steg."
    )
    add("")

    if supplement is not None:
        add("## Kompletterande matris utan överträningsvakt")
        add("")
        add(
            "Vakten stoppar träningen innan modellen hunnit lära sig något på det här "
            "datasetet, så den första matrisen kan inte skilja variationstyperna från "
            "varandra. Den kompletterande matrisen kör samma konfigurationer med "
            "`--overfitting-guard off`, alltså appens träning utan early stopping, så alla "
            "körningar går de 100 epokerna. Det är en avvikelse från uppgiftens "
            "genomförandemall, som säger att överträningsdetektionen ska vara aktiverad; "
            "den finns med för att frågan om variationernas effekt annars inte går att "
            "besvara. Bästa checkpoint väljs fortfarande på träningens egen valdel."
        )
        add("")
        add("### Körningarna")
        add("")
        add(_table(RUN_HEADER, _run_rows(supplement["grouped"])))
        add("")
        supplement_baseline = supplement["summaries"]["baseline"]["map50_95"]
        add("### Variationstyper mot baslinjen")
        add("")
        add(
            _chart_link(
                supplement["charts"]["types"], report_path, "Variationstyper utan vakt"
            )
        )
        add("")
        add(_table(TYPE_HEADER, _type_rows(supplement["summaries"], supplement_baseline)))
        add("")
        add(_ranking_line(supplement["summaries"]))
        add("")
        add("Per vy, mAP50-95 (medel över upprepningarna):")
        add("")
        add(
            _table(
                ["Konfiguration", *_views(supplement["payload"]["runs"])],
                _view_rows(
                    supplement["summaries"],
                    supplement["grouped"],
                    _views(supplement["payload"]["runs"]),
                ),
            )
        )
        add("")
        add("### Antal variationer per bildpar")
        add("")
        add(
            _chart_link(
                supplement["charts"]["counts"], report_path, "Antal variationer utan vakt"
            )
        )
        add("")
        add(_table(COUNT_HEADER, _count_rows(supplement["summaries"], supplement_baseline)))
        add("")
        add("### Spridning mellan upprepningar")
        add("")
        add(
            _table(
                SPREAD_HEADER,
                _spread_rows(supplement["summaries"], supplement["grouped"]),
            )
        )
        add("")

    control_summaries = _control_summaries(base)
    control = _control_section(base, summaries, control_summaries)
    if control:
        lines.extend(control)
        add("")

    comparison = _comparison(base, summaries)
    if comparison:
        lines.extend(comparison)
        add("")

    add("## Resonemang")
    add("")
    add(_reasoning(summaries, baseline, grouped, supplement, base, control_summaries))
    add("")

    add("## Begränsningar")
    add("")
    add(_limitations(split, base))
    add("")

    add("## Rekommendation")
    add("")
    add(_recommendation(summaries, baseline, supplement, control_summaries))
    add("")
    add("## Underlag")
    add("")
    roots = [work_root]
    if supplement is not None:
        roots.append(supplement_root)
    if base.control_root is not None and (base.control_root / "runs").exists():
        roots.append(base.control_root)
    add(
        "Resultatfilerna ligger i "
        + " och ".join(f"`{_display_path(root)}`" for root in roots)
        + " utanför repot: `results.json` med alla körningar, och `runs/<körnings-id>/` med "
        "dataset, export, träningsmanifest och modell för varje körning. Skriptet som tog "
        "fram dem är `scripts/variation_eval.py`."
    )
    add("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapporten skriven till {report_path}")


def _control_summaries(base: BaseModel) -> dict[str, dict] | None:
    """Sammanfattningen av kontrollkörningarna, eller None när ingen finns."""
    if base.control_root is None:
        return None
    payload = _load_results(base.control_root, base.family)
    if not payload["runs"]:
        return None
    return {key: _summary(value) for key, value in _by_config(payload["runs"]).items()}


def _control_section(
    base: BaseModel, summaries: dict[str, dict], control: dict[str, dict] | None
) -> list[str]:
    """Kontrollkörningarna med vakten av, för en basmodell där hela matrisen inte ryms."""
    if control is None:
        return []
    rows = [
        [
            CONFIG_BY_KEY[key].label,
            f"{summaries[key]['map50_95']:.3f}",
            f"{summaries[key]['epochs']:.0f}",
            f"{control[key]['map50_95']:.3f}",
            f"{control[key]['epochs']:.0f}",
        ]
        for key in TYPE_KEYS
        if key in control and key in summaries
    ]
    if not rows:
        return []
    lines = [
        "## Kontroll med överträningsvakten av",
        "",
        f"Hela matrisen utan vakt skulle ta över tio timmar med {base.label}, eftersom "
        "varje körning då går 100 epoker. Kontrollen kör därför bara de konfigurationer "
        "som behövs för att avgöra om vakten orsakar kollapsen: baslinjen, rotation och "
        "färg, ett frön var.",
        "",
        _table(
            ["Konfiguration", "mAP50-95 med vakt", "Epoker", "mAP50-95 utan vakt", "Epoker"],
            rows,
        ),
        "",
    ]
    recovered = [
        key
        for key in control
        if key in summaries and control[key]["map50_95"] > summaries[key]["map50_95"] + 0.05
    ]
    if not recovered:
        lines.append(
            "Utan vakt stiger ingen av kontrollens konfigurationer tydligt, alltså står sig "
            "resultatet: variationen skadar modellen även när träningen får gå 100 epoker."
        )
        return lines
    baseline = summaries["baseline"]["map50_95"]
    level = [key for key in recovered if control[key]["map50_95"] >= baseline - 0.02]
    below = [key for key in recovered if key not in level]
    parts = [
        "Utan vakt stiger "
        + _join_labels(recovered)
        + " tydligt, alltså lärde sig modellen mer när träningen fick fortsätta."
    ]
    if level:
        parts.append(
            f" {_join_labels(level)} når då samma nivå som baslinjen, så kollapsen i "
            "matrisen med vakt beror helt på att träningen stoppades."
        )
    if below:
        parts.append(
            f" {_join_labels(below)} återhämtar sig men når inte baslinjen, så den "
            "variationen skadar modellen även när träningen får gå 100 epoker."
        )
    lines.append("".join(parts))
    return lines


def _join_labels(keys: list[str]) -> str:
    """Konfigurationsetiketterna som en uppräkning med svenskt och."""
    labels = [CONFIG_BY_KEY[key].label for key in keys]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " och " + labels[-1]


def _comparison(base: BaseModel, summaries: dict[str, dict]) -> list[str]:
    """Jämförelsen med YOLO-körningen i TASK-160, för en annan basmodell."""
    if base.family == "yolo":
        return []
    other = BASES["yolo"]
    other_payload = _load_results(other.work_root, other.family)
    if not other_payload["runs"]:
        return []
    other_summaries = {
        key: _summary(value) for key, value in _by_config(other_payload["runs"]).items()
    }
    rows = [
        [
            CONFIG_BY_KEY[key].label,
            f"{other_summaries[key]['map50_95']:.3f}",
            f"{summaries[key]['map50_95']:.3f}",
        ]
        for key in TYPE_KEYS
        if key in summaries and key in other_summaries
    ]
    if not rows:
        return []
    lines = [
        "## Jämförelse med YOLO-körningen",
        "",
        f"Samma matris kördes i TASK-160 med {other.label}. Tabellen ställer de två "
        "basmodellerna mot varandra med överträningsvakten på, alltså appens "
        "standardinställning.",
        "",
        _table(["Konfiguration", other.label, base.label], rows),
        "",
    ]
    other_baseline = other_summaries["baseline"]["map50_95"]
    baseline = summaries["baseline"]["map50_95"]
    lines.append(
        f"Baslinjen ligger på {baseline:.3f} för {base.label} mot {other_baseline:.3f} för "
        f"{other.label}. "
        + (
            "Den här basmodellen klarar alltså datasetet betydligt bättre redan utan "
            "variationer, vilket är väntat: den är tränad på röntgenbilder sedan tidigare."
            if baseline > other_baseline
            else "Den här basmodellen klarar alltså datasetet sämre än YOLO26 medium utan "
            "variationer."
        )
    )
    lines.append("")
    best = max(
        (key for key in TYPE_KEYS if key in summaries and key != "baseline"),
        key=lambda key: summaries[key]["map50_95"],
    )
    lines.append(
        f"För {base.label} är baslinjen {baseline:.3f} och den bästa variationstypen "
        f"{CONFIG_BY_KEY[best].label} {summaries[best]['map50_95']:.3f}. "
        + (
            "Slutsatsen från TASK-160 håller: ingen variationstyp slår baslinjen."
            if summaries[best]["map50_95"] <= baseline
            else "Till skillnad från TASK-160 slår en variationstyp baslinjen här."
        )
    )
    lines.append("")
    lines.append(
        f"YOLO-siffrorna i tabellen är från matrisen med vakten på, där vakten stoppade "
        f"varje körning innan modellen lärt sig något; de säger alltså inget om vilken "
        f"variationstyp som är bäst för {other.label}. Jämförelsen som håller är att "
        f"baslinjen för {base.label} ligger på en användbar nivå medan "
        f"{other.label} behöver matrisen utan vakt för att komma dit."
    )
    return lines


def _summary_bullets(
    summaries: dict[str, dict], baseline: float, supplement: dict | None
) -> str:
    """Punktlistan som inleder rapporten."""
    epochs = [summary["epochs"] for summary in summaries.values()]
    ranked = sorted(
        (key for key in TYPE_KEYS if key in summaries and key != "baseline"),
        key=lambda key: summaries[key]["map50_95"],
        reverse=True,
    )
    best_key = ranked[0]
    best = summaries[best_key]["map50_95"]
    bullets = [
        f"* Med appens standardinställning, alltså överträningsvakten på, stoppade vakten "
        f"varje körning efter {min(epochs):.0f}–{max(epochs):.0f} epoker. Baslinjen ligger "
        f"på mAP50-95 {baseline:.3f} och den bästa variationstypen, "
        f"{CONFIG_BY_KEY[best_key].label}, på {best:.3f}."
    ]
    difference = best - baseline
    spread = max(
        summaries[best_key]["map50_95_std"], summaries["baseline"]["map50_95_std"]
    )
    if difference <= spread:
        if difference < 0:
            bullets.append(
                f"* Ingen variationstyp når baslinjen: den bästa ligger {abs(difference):.3f} "
                f"under, och spridningen är {spread:.3f}."
            )
        else:
            bullets.append(
                f"* Ingen variationstyp går att skilja från baslinjen: den bästa ligger "
                f"{difference:+.3f} ifrån, alltså mindre än spridningen på {spread:.3f}."
            )
    else:
        bullets.append(
            f"* {CONFIG_BY_KEY[best_key].label} slår baslinjen med {difference:+.3f}, mer än "
            f"spridningen på {spread:.3f}."
        )
    counts = [
        (COUNT_VALUES[key], summaries[key]["map50_95"])
        for key in COUNT_VALUES
        if key in summaries
    ]
    if counts:
        best_count, best_value = max(counts, key=lambda item: item[1])
        unit = "variation" if best_count == 1 else "variationer"
        if best_value <= baseline:
            bullets.append(
                f"* Ingen kombination når baslinjen heller: den bästa, {best_count} {unit} "
                f"per bildpar, ger {best_value:.3f}."
            )
        else:
            bullets.append(
                f"* I matrisen med vakten på toppar kurvan vid {best_count} {unit} per "
                f"bildpar med mAP50-95 {best_value:.3f}, mot baslinjens {baseline:.3f}."
            )
    if supplement is not None:
        supplement_summaries = supplement["summaries"]
        supplement_baseline = supplement_summaries["baseline"]["map50_95"]
        supplement_ranked = sorted(
            (
                key
                for key in TYPE_KEYS
                if key in supplement_summaries and key != "baseline"
            ),
            key=lambda key: supplement_summaries[key]["map50_95"],
            reverse=True,
        )
        supplement_best = supplement_ranked[0]
        bullets.append(
            f"* Utan vakt, där alla körningar går 100 epoker, ligger baslinjen på "
            f"{supplement_baseline:.3f} och den bästa variationstypen, "
            f"{CONFIG_BY_KEY[supplement_best].label}, på "
            f"{supplement_summaries[supplement_best]['map50_95']:.3f}."
        )
        supplement_counts = [
            supplement_summaries[key]["map50_95"]
            for key in COUNT_VALUES
            if key in supplement_summaries
        ]
        if supplement_counts:
            relation = (
                "under" if max(supplement_counts) <= supplement_baseline else "kring"
            )
            bullets.append(
                f"* Utan vakt ger 1–20 variationer per bildpar "
                f"{min(supplement_counts):.3f}–{max(supplement_counts):.3f}, alltså "
                f"{relation} baslinjens {supplement_baseline:.3f}."
            )
    return "\n".join(bullets)


def _limitations(split: dict, base: BaseModel) -> str:
    """Begränsningarna som punktlista."""
    return "\n".join(
        [
            f"* Utvärderingsuppsättningen är {split['eval_pairs']} bildpar, "
            f"{split['eval_pairs'] * 2} bilder och {split['eval_objects']} objekt. Ett enda "
            "objekt flyttar mAP med ungefär en tiondel, så skillnader under ungefär 0,05 ska "
            "läsas som brus även när de är större än spridningen mellan upprepningarna.",
            "* Träningen ser bara sex bildpar (tolv bilder) efter appens egen "
            "train/val-delning av de åtta paren. Det är den situation uppgiften beskriver, "
            "men det gör också att både baslinjen och variationerna ligger på en låg nivå.",
            "* Utvärderingsuppsättningen saknar bilder utan objekt, så appens falsklarm per "
            "bild kan inte skilja konfigurationerna. Falska detektioner per bild är ett "
            "komplement som räknar larm som inte matchar något facit.",
            "* Styrkorna är dialogens standardvärden. Rapporten säger inget om hur en mindre "
            "rotationsvinkel eller en svagare färgändring hade fallit ut.",
            f"* Basmodellen är {base.label}. En annan basmodell kan svara annorlunda på "
            "samma variationer.",
            "* Antalet variationer per bildpar ändrar också antalet optimeringssteg per "
            "epok, eftersom träningsmängden växer. Rapporten mäter alltså utökningens "
            "samlade effekt, inte en isolerad variationseffekt vid konstant stegantal.",
            "* Falska detektioner per bild mäts vid driftströskeln. När modellen inte lärt "
            "sig något hamnar tröskeln på 0,01 och antalet larm når detektorns tak på 300 "
            "rutor per bild, så talet ska läsas som en storleksordning och inte som ett "
            "exakt antal.",
        ]
    )


def _reasoning(
    summaries: dict[str, dict],
    baseline: float,
    grouped: dict[str, list[dict]],
    supplement: dict | None,
    base: BaseModel,
    control: dict[str, dict] | None,
) -> str:
    """Resonemanget kring tabellerna, som en punktlista."""
    parts = [
        "* Med överträningsvakten på stoppade den varje körning. Med tolv träningsbilder "
        f"och batch {base.batch} blir det bara ett fåtal optimeringssteg per epok, så "
        "vaktens tio epoker utan förbättring räcker inte för att modellen ska hinna lära "
        "sig något."
    ]
    if "all-5" in summaries:
        steps = summaries["all-5"]["train_images"] // base.batch
        if summaries["all-5"]["map50_95"] > baseline:
            parts.append(
                f"* Kombinationen lyfte först vid 5 variationer per bildpar, där "
                f"{summaries['all-5']['train_images']} träningsbilder ger {steps} steg per "
                "epok. Då räcker vaktens tio epoker tillräckligt många steg för att "
                "valvärdet ska röra sig, och träningen får fortsätta."
            )
        else:
            parts.append(
                f"* Kombinationen når inte över baslinjen heller: 5 variationer per bildpar "
                f"ger {summaries['all-5']['map50_95']:.3f} mot {baseline:.3f}, trots att "
                f"{summaries['all-5']['train_images']} träningsbilder ger {steps} steg per "
                "epok. Fler steg räddar alltså inte resultatet."
            )
    if supplement is not None:
        supplement_summaries = supplement["summaries"]
        supplement_baseline = supplement_summaries["baseline"]["map50_95"]
        parts.append(
            "* Utan vakt går alla körningar 100 epoker, och då går typerna att jämföra. "
            "Varje typ har samma antal träningsbilder som de andra, så skillnaden mellan "
            "dem är en skillnad i variationen och inte i stegantal."
        )
        for key in TYPE_KEYS:
            if key not in supplement_summaries or key == "baseline":
                continue
            summary = supplement_summaries[key]
            difference = summary["map50_95"] - supplement_baseline
            spread = max(
                summary["map50_95_std"], supplement_summaries["baseline"]["map50_95_std"]
            )
            if difference > spread:
                verdict = "ligger över baslinjen även med spridningen inräknad"
            elif difference < -spread:
                verdict = "ligger under baslinjen även med spridningen inräknad"
            else:
                verdict = "går inte att skilja från baslinjen"
            parts.append(
                f"* **{CONFIG_BY_KEY[key].label}** ger {difference:+.3f} mAP50-95 mot "
                f"baslinjen utan vakt och {verdict} (spridning {spread:.3f})."
            )
        counts = [
            (COUNT_VALUES[key], supplement_summaries[key]["map50_95"])
            for key in COUNT_KEYS
            if key in COUNT_VALUES and key in supplement_summaries
        ]
        if counts:
            best_count, best_value = max(counts, key=lambda item: item[1])
            if best_value <= supplement_baseline:
                unit = "variation" if best_count == 1 else "variationer"
                parts.append(
                    f"* Ingen av kombinationerna når baslinjen: den bästa, {best_count} "
                    f"{unit} per bildpar, ger {best_value:.3f} mot baslinjens "
                    f"{supplement_baseline:.3f}. Fler variationer räddar alltså inte ett "
                    "resultat som en enda variation försämrar."
                )
            else:
                parts.append(
                    f"* Kurvan över antal variationer toppar vid **{best_count} variationer "
                    f"per bildpar** med mAP50-95 {best_value:.3f}."
                )
        parts.append(
            "* Ingen övre gräns kunde fastställas: kurvan når aldrig baslinjen inom det "
            "testade intervallet 1–20 variationer per bildpar, så det finns ingen nivå där "
            "fler variationer slutar förbättra. De förbättrar aldrig, och efter 10 "
            "variationer vänder kurvan svagt uppåt igen utan att komma i närheten."
        )
        parts.append(
            "* Per vy syns ett mönster som gäller alla typer: de höjer mAP på vy 1 men "
            "sänker den på vy 2. Bildparet är samma scen från två håll, och en speglad, "
            "roterad eller skalad bild är ingen bild som kamerorna kan producera. En rimlig "
            "förklaring är att modellen lär sig kännetecken som bara finns i de syntetiska "
            "bilderna och tappar den vy där originalen är svårast, men rapporten mäter inte "
            "orsaken."
        )
    collapsed = [
        key
        for key in TYPE_KEYS
        if key in summaries and key != "baseline" and summaries[key]["map50_95"] == 0
    ]
    if collapsed:
        text = (
            "* "
            + _join_labels(collapsed)
            + " kollapsar helt i matrisen med vakt: alla upprepningar ger mAP50-95 0.000, "
            "och modellen larmar bara någon enstaka gång per bild."
        )
        recovered = [
            key
            for key in collapsed
            if control is not None and key in control and control[key]["map50_95"] > 0.05
        ]
        if recovered:
            text += (
                f" Kontrollen utan vakt visar att {_join_labels(recovered)} återhämtar sig "
                "när träningen får gå 100 epoker, så kollapsen är vaktens fel och inte "
                "variationens."
            )
        parts.append(text)
    parts.append(
        "* Skillnaden mellan intilliggande steg ska jämföras med spridningen i tabellerna; "
        "ett steg som rör sig mindre än spridningen säger inget."
    )
    return "\n".join(parts)


def _recommendation(
    summaries: dict[str, dict],
    baseline: float,
    supplement: dict | None,
    control: dict[str, dict] | None,
) -> str:
    """Rekommendationen rapporten avslutas med."""
    source = supplement["summaries"] if supplement is not None else summaries
    source_baseline = source["baseline"]["map50_95"]
    ranked = sorted(
        (key for key in TYPE_KEYS if key in source and key != "baseline"),
        key=lambda key: source[key]["map50_95"],
        reverse=True,
    )
    if not ranked:
        return "Inga variationstyper kunde jämföras."
    best = ranked[0]
    summary = source[best]
    difference = summary["map50_95"] - source_baseline
    spread = max(summary["map50_95_std"], source["baseline"]["map50_95_std"])
    if difference <= spread:
        worse = [
            key
            for key in ranked
            if source[key]["map50_95"]
            < source_baseline
            - max(source[key]["map50_95_std"], source["baseline"]["map50_95_std"])
        ]
        text = (
            "Ingen av de testade variationstyperna slår baslinjen: den bästa ligger på "
            f"{summary['map50_95']:.3f} mot baslinjens {source_baseline:.3f}, och skillnaden "
            f"är mindre än spridningen på {spread:.3f}."
        )
        if worse:
            text += (
                f" {_join_labels(worse)} ligger dessutom under baslinjen även med "
                "spridningen inräknad, alltså sämre än att inte utöka alls."
            )
        if control is not None:
            recovered = [
                key
                for key in worse
                if key in control and control[key]["map50_95"] >= source_baseline - 0.02
            ]
            if recovered:
                text += (
                    f" Kontrollen utan vakt visar dock att {_join_labels(recovered)} når "
                    "baslinjen när träningen får gå 100 epoker, så för den variationen är "
                    "det vakten och inte variationen som avgör."
                )
        return (
            f"{text} Vid ett tiotal bildpar är rekommendationen att träna på de manuellt "
            "annoterade bildparen som de är och lägga arbetet på fler annoterade bildpar i "
            "stället: en utökning som inte går att skilja från baslinjen kostar träningstid "
            "utan att ge något."
        )
    counts = [
        (COUNT_VALUES[key], source[key]["map50_95"])
        for key in COUNT_KEYS
        if key in COUNT_VALUES and key in source
    ]
    plateau = ""
    if counts:
        best_count, best_value = max(counts, key=lambda item: item[1])
        plateau = (
            f" Kurvan planar ut vid {best_count} variationer per bildpar "
            f"(mAP50-95 {best_value:.3f}); fler än så gav ingen ytterligare förbättring."
        )
    return (
        f"Vid ett tiotal bildpar är **{CONFIG_BY_KEY[best].label}** den variation som gav "
        f"bäst resultat: mAP50-95 {summary['map50_95']:.3f} mot baslinjens "
        f"{source_baseline:.3f} ({difference:+.3f}), vilket är större än spridningen på "
        f"{spread:.3f}.{plateau} Använd den kombinationen, och räkna med att appens "
        "överträningsvakt stoppar träningen innan modellen lärt sig något om datasetet bara "
        "har ett tiotal bildpar: lägg till fler annoterade bildpar innan du litar på "
        "resultatet."
    )


def _use_utf8_output() -> None:
    """Skriver svenska tecken som UTF-8 även när konsolen är cp1252."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(OSError, ValueError):
            reconfigure(encoding="utf-8")


def main() -> None:
    _use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "report"))
    parser.add_argument(
        "--only",
        default="",
        help="kommaseparerade konfigurationsnycklar för run, t.ex. baseline,rotation",
    )
    parser.add_argument(
        "--base",
        default="yolo",
        choices=tuple(BASES),
        help="basmodellen matrisen körs med",
    )
    parser.add_argument("--work-root", default="")
    parser.add_argument(
        "--seeds",
        default="",
        help="kommaseparerade frön för run; tomt ger VARIATION_SEEDS",
    )
    parser.add_argument(
        "--guard",
        default="on",
        choices=("on", "off"),
        help="överträningsvaktens läge; off används för den kompletterande matrisen",
    )
    args = parser.parse_args()
    base = BASES[args.base]
    work_root = Path(args.work_root) if args.work_root else base.work_root
    if args.command == "prepare":
        prepare(work_root)
    elif args.command == "run":
        only = [key for key in args.only.split(",") if key]
        seeds = tuple(int(value) for value in args.seeds.split(",") if value)
        run_matrix(work_root, only or None, args.guard, base, seeds or VARIATION_SEEDS)
    else:
        report(base)


if __name__ == "__main__":
    main()
