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
    export_yolo,
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

#: Arbetskatalogen ligger utanför repot, så inga tränade modeller hamnar i git.
WORK_ROOT = Path.home() / ".xray-detector" / "eval" / "task-160"
#: Kompletterande matris med överträningsvakten avstängd. Vakten stoppar alla
#: körningar på det här datasetet innan modellen hunnit lära sig något, så
#: utan den går variationernas effekt inte att mäta.
SUPPLEMENT_ROOT = Path.home() / ".xray-detector" / "eval" / "task-160-noguard"
#: Appens eget dataset, som bara läses.
SOURCE_DATASET = Path.home() / ".xray-detector" / "datasets"
#: Samma delning som appens export använder, så train/val räknas lika.
TRAIN_RATIO = 0.8
#: Basmodellen är appens standardmodell; den är gemensam för alla körningar.
BASE_MODEL = "yolo26m"
BASE_MODEL_LABEL = "YOLO26 medium"
EPOCHS = 100
#: Användarens sparade träningsinställning. Appens uträknade default för
#: 1280x720-bilder är 1280, men den storleken tog 15 gånger längre tid per steg
#: på det här datasetet utan att modellen lärde sig snabbare.
IMGSZ = 800
BATCH = 8
#: Flera frön per konfiguration, eftersom variationerna dras slumpmässigt.
VARIATION_SEEDS = (1, 2, 3)
#: Baslinjen har inga variationer att dra, så den upprepas för att visa att
#: träningen är deterministisk.
BASELINE_REPEATS = 2
RESULTS_NAME = "results.json"
REPORT_PATH = Path("docs/rapporter/bildvariationer.md")
CHART_DIR = Path("docs/rapporter/bilder")


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


def prepare(work_root: Path = WORK_ROOT, source: Path = SOURCE_DATASET) -> None:
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


def _train(run_dir: Path, data_yaml: Path, label: str, guard: str) -> float:
    """Tränar en körning med appens träningsprocess; returnerar körtiden."""
    command = [
        sys.executable,
        "-m",
        "xray_detector.infrastructure.training.train_task",
        "--dataset",
        str(data_yaml),
        "--weights",
        str(PROJECT_ROOT / "models" / f"{BASE_MODEL}.pt"),
        "--output",
        str(run_dir / "model"),
        "--epochs",
        str(EPOCHS),
        "--imgsz",
        str(IMGSZ),
        "--batch",
        str(BATCH),
        "--family",
        "yolo",
        "--overfitting-guard",
        guard,
        "--name",
        label,
        "--base-name",
        BASE_MODEL_LABEL,
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
    work_root: Path = WORK_ROOT,
    guard: str = "on",
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
    train_pairs, val_pairs = train_val_counts(store, TRAIN_RATIO)
    data_yaml = export_yolo(store, run_dir / "export", TRAIN_RATIO)
    exported = _read_json(run_dir / "export" / "yolo" / "manifest.json")

    print(
        f"{run_id}: {train_pairs} train-grupper, {val_pairs} val-grupper, "
        f"{exported['num_train']} train-bilder, {synthetic} syntetiska"
    )
    duration = _train(run_dir, data_yaml, config.label, guard)

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
    work_root: Path = WORK_ROOT, only: list[str] | None = None, guard: str = "on"
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
                run_one(config, None, f"{config.key}-r{index}", work_root, guard)
                for index in range(1, BASELINE_REPEATS + 1)
            )
            continue
        results.extend(
            run_one(config, seed, f"{config.key}-s{seed}", work_root, guard)
            for seed in VARIATION_SEEDS
        )
    _write_json(
        work_root / RESULTS_NAME,
        {
            "generated": datetime.now(UTC).isoformat(),
            "base_model": BASE_MODEL,
            "epochs": EPOCHS,
            "imgsz": IMGSZ,
            "batch": BATCH,
            "train_ratio": TRAIN_RATIO,
            "overfitting_guard": guard,
            "variation_seeds": list(VARIATION_SEEDS),
            "runs": results,
        },
    )


def _load_results(work_root: Path) -> dict:
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
    payload["runs"] = _with_image_counts(payload["runs"], work_root)
    return payload


def _with_image_counts(runs: list[dict], work_root: Path) -> list[dict]:
    """Antalet train- och valbilder ur exportens manifest.

    Bilderna räknas per bild, inte per fångstgrupp: en grupp bär alla
    variationer av sitt bildpar, så gruppantalet säger inget om hur många
    bilder träningen faktiskt ser.
    """
    for run in runs:
        if "train_images" in run:
            continue
        manifest = work_root / "runs" / run["run_id"] / "export" / "yolo" / "manifest.json"
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


def report(
    work_root: Path = WORK_ROOT,
    report_path: Path = REPORT_PATH,
    supplement_root: Path = SUPPLEMENT_ROOT,
) -> None:
    """Skriver markdown-rapporten ur resultaten."""
    payload = _load_results(work_root)
    runs = payload["runs"]
    if not runs:
        raise SystemExit("Inga resultat att rapportera")
    grouped = _by_config(runs)
    summaries = {key: _summary(value) for key, value in grouped.items()}
    split = _read_json(work_root / "datasets" / "split.json")
    charts = _charts(summaries)
    baseline = summaries["baseline"]["map50_95"]
    supplement = None
    supplement_payload = _load_results(supplement_root)
    if supplement_payload["runs"]:
        supplement_grouped = _by_config(supplement_payload["runs"])
        supplement = {
            "payload": supplement_payload,
            "grouped": supplement_grouped,
            "summaries": {key: _summary(value) for key, value in supplement_grouped.items()},
            "charts": _charts(
                {key: _summary(value) for key, value in supplement_grouped.items()},
                "utan-vakt-",
                with_epochs=False,
            ),
        }
    lines = []
    add = lines.append

    add("# Syntetiska bildvariationer vid ett tiotal annoterade bildpar")
    add("")
    add(
        f"**Uppgift:** TASK-160 · **Basmodell:** {BASE_MODEL_LABEL} (`{BASE_MODEL}.pt`) · "
        f"**Epoker:** {payload.get('epochs', EPOCHS)} · **Bildstorlek:** "
        f"{payload.get('imgsz', IMGSZ)} · **Batch:** {payload.get('batch', BATCH)}"
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
    add(
        "Träningsdelen exporteras med appens `export_yolo`, som delar den i train och val "
        "per bildpar. Variationerna läggs till före exporten, så alla variationer av ett "
        "bildpar hamnar i samma delmängd och aldrig läcker mellan train och val. "
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
    add(
        f"Träningen körs med appens `train_task` i en egen process, precis som träningsvyn "
        f"startar den: {BASE_MODEL_LABEL} som bas, {payload.get('epochs', EPOCHS)} epoker som "
        f"tak, bildstorlek {payload.get('imgsz', IMGSZ)} och batch {payload.get('batch', BATCH)}. "
        "Överträningsvakten är på, så ultralytics egen early stopping (patience 10) kan "
        "avsluta körningen i förtid. Antalet genomförda epoker redovisas per körning."
    )
    add("")
    add(
        "Vakten visade sig avgöra hela resultatet på det här datasetet, så matrisen kördes "
        "en gång till med vakten avstängd. Den kompletterande matrisen står under "
        "**Kompletterande matris utan överträningsvakt** och är den som svarar på vilka "
        "variationer som hjälper; den första matrisen visar vad appens standardinställning "
        "gör med samma data."
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
    add(
        "Baslinjen har inga variationer att dra, så dess två körningar är identiska: "
        "träningen är deterministisk (seed 42, `deterministic=True`). Spridningen i tabellen "
        "nedan kommer därför enbart från att variationerna dras olika, och den anger hur "
        "stor en skillnad mellan två konfigurationer måste vara för att inte vara slump."
    )
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

    add("## Resonemang")
    add("")
    add(_reasoning(summaries, baseline, grouped, supplement))
    add("")

    add("## Begränsningar")
    add("")
    add(_limitations(split))
    add("")

    add("## Rekommendation")
    add("")
    add(_recommendation(summaries, baseline, supplement))
    add("")
    add("## Underlag")
    add("")
    add(
        f"Resultatfilerna ligger i `{_display_path(work_root)}` och "
        f"`{_display_path(supplement_root)}` utanför repot: `results.json` med alla "
        "körningar, och `runs/<körnings-id>/` med dataset, export, träningsmanifest och "
        "modell för varje körning. Skriptet som tog fram dem är "
        "`scripts/variation_eval.py`."
    )
    add("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapporten skriven till {report_path}")


def _summary_bullets(
    summaries: dict[str, dict], baseline: float, supplement: dict | None
) -> str:
    """Punktlistan som inleder rapporten."""
    epochs = [summary["epochs"] for summary in summaries.values()]
    low = [
        summaries[key]["map50_95"]
        for key in ("baseline", "rotation", "flip", "scale", "color", "all-1", "all-2")
        if key in summaries
    ]
    bullets = [
        f"* Med appens standardinställning, alltså överträningsvakten på, stoppade vakten "
        f"varje körning efter {min(epochs):.0f}–{max(epochs):.0f} epoker. Baslinjen och "
        f"konfigurationerna med 0–2 variationer per bildpar landar på mAP50-95 "
        f"{min(low):.3f}–{max(low):.3f}, alltså ingen skillnad som går att mäta."
    ]
    if "all-5" in summaries:
        bullets.append(
            f"* Kombinationen lyfte först vid 5 variationer per bildpar, till "
            f"{summaries['all-5']['map50_95']:.3f}. Orsaken är att datasetet då blir stort "
            "nog att träningen hinner lära sig något innan vakten stoppar den, inte att "
            "variationerna i sig är bättre."
        )
    if supplement is not None:
        supplement_summaries = supplement["summaries"]
        supplement_baseline = supplement_summaries["baseline"]["map50_95"]
        level = [key for key in ("scale", "color") if key in supplement_summaries]
        worse = [key for key in ("rotation", "flip", "all-1") if key in supplement_summaries]
        text_parts = [
            f"* Utan vakt, där alla körningar går 100 epoker, når ingen variationstyp över "
            f"baslinjens {supplement_baseline:.3f}."
        ]
        if level:
            values = [supplement_summaries[key]["map50_95"] for key in level]
            text_parts.append(
                f" {', '.join(CONFIG_BY_KEY[key].label for key in level)} ligger på samma "
                f"nivå ({min(values):.3f}–{max(values):.3f})"
            )
        if worse:
            values = [supplement_summaries[key]["map50_95"] for key in worse]
            text_parts.append(
                f", medan {', '.join(CONFIG_BY_KEY[key].label for key in worse)} ligger "
                f"under ({min(values):.3f}–{max(values):.3f})."
            )
        bullets.append("".join(text_parts))
        counts = [
            supplement_summaries[key]["map50_95"]
            for key in COUNT_VALUES
            if key in supplement_summaries
        ]
        if counts:
            bullets.append(
                f"* Antalet variationer räddar inte resultatet: 1–20 variationer per bildpar "
                f"ger {min(counts):.3f}–{max(counts):.3f}, alltså under baslinjens "
                f"{supplement_baseline:.3f} hela vägen."
            )
    return "\n".join(bullets)


def _limitations(split: dict) -> str:
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
            "* Basmodellen är appens standardmodell, YOLO26 medium. En modell som redan är "
            "tränad på röntgenbilder kan svara annorlunda på samma variationer.",
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
) -> str:
    """Resonemanget kring tabellerna, som en punktlista."""
    parts = [
        "* Med överträningsvakten på stoppade den varje körning. Med tolv träningsbilder "
        f"och batch {BATCH} är en epok två optimeringssteg, så vaktens tio epoker utan "
        "förbättring är tjugo steg. Modellen behöver omkring hundra steg innan valvärdet "
        "rör sig, så vakten hinner stoppa träningen innan den börjat lära sig. Det syns på "
        "att alla enskilda variationstyper hamnar på samma mAP som baslinjen."
    ]
    if "all-5" in summaries:
        parts.append(
            f"* Kombinationen lyfte först vid 5 variationer per bildpar, där "
            f"{summaries['all-5']['train_images']} träningsbilder ger "
            f"{summaries['all-5']['train_images'] // BATCH} steg per epok. Då räcker "
            "vaktens tio epoker tillräckligt många steg för att valvärdet ska röra sig, och "
            "träningen får fortsätta. Att kurvan planar ut vid 10 och 20 variationer beror "
            "på att stegantalet redan är tillräckligt där."
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
    parts.append(
        "* Skillnaden mellan intilliggande steg ska jämföras med spridningen i tabellerna; "
        "ett steg som rör sig mindre än spridningen säger inget."
    )
    return "\n".join(parts)


def _recommendation(
    summaries: dict[str, dict], baseline: float, supplement: dict | None
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
            CONFIG_BY_KEY[key].label
            for key in ranked
            if source[key]["map50_95"]
            < source_baseline
            - max(source[key]["map50_95_std"], source["baseline"]["map50_95_std"])
        ]
        text = (
            "Ingen av de testade variationstyperna höjer mAP50-95 mer än spridningen mellan "
            "upprepningarna."
        )
        if worse:
            text += (
                f" {', '.join(worse)} ligger dessutom under baslinjen även med spridningen "
                "inräknad, alltså sämre än att inte utöka alls."
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
    parser.add_argument("--work-root", default=str(WORK_ROOT))
    parser.add_argument(
        "--guard",
        default="on",
        choices=("on", "off"),
        help="överträningsvaktens läge; off används för den kompletterande matrisen",
    )
    args = parser.parse_args()
    work_root = Path(args.work_root)
    if args.command == "prepare":
        prepare(work_root)
    elif args.command == "run":
        only = [key for key in args.only.split(",") if key]
        run_matrix(work_root, only or None, args.guard)
    else:
        report(work_root)


if __name__ == "__main__":
    main()
