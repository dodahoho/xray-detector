"""Unik snapshot av bästa vikterna per träningskörning (TASK-47)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from xray_detector.application.model_registry import trained_models
from xray_detector.infrastructure.training.train_task import (
    MANIFEST_NAME,
    _best_checkpoint,
    _output_path,
    _prepare_run_dir,
    _RunState,
    _write_manifest,
)


def _args(output_path: Path, **overrides):
    values = {
        "family": "yolo",
        "weights": "yolo26n.pt",
        "output_path": output_path,
        "dataset": str(output_path / "data.yaml"),
        "epochs": 10,
        "imgsz": 640,
        "batch": 16,
        "device": "cpu",
        "overfitting_guard": "on",
        "started": datetime(2026, 11, 12, 10, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _yolo_weights(run_dir: Path) -> Path:
    weights = run_dir / "yolo" / "weights" / "best.pt"
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"vikter")
    return weights


def _rfdetr_weights(run_dir: Path, name: str) -> Path:
    weights = run_dir / "rfdetr" / name
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"vikter")
    return weights


# --- Unik körningskatalog (AC 1, 2) ---


def test_first_run_uses_the_given_directory(tmp_path):
    run_dir = _prepare_run_dir(_args(tmp_path / "korning"))

    assert run_dir == tmp_path / "korning"
    assert run_dir.is_dir()


def test_second_run_with_the_same_output_gets_its_own_directory(tmp_path):
    first = _prepare_run_dir(_args(tmp_path / "korning"))
    _yolo_weights(first)
    _write_manifest(_args(first), first, _RunState(status="completed"))

    second = _prepare_run_dir(_args(tmp_path / "korning"))

    assert second == tmp_path / "korning_2"
    assert second.is_dir()


def test_third_run_keeps_counting(tmp_path):
    for _ in range(2):
        run_dir = _prepare_run_dir(_args(tmp_path / "korning"))
        _yolo_weights(run_dir)
        _write_manifest(_args(run_dir), run_dir, _RunState(status="completed"))

    third = _prepare_run_dir(_args(tmp_path / "korning"))

    assert third == tmp_path / "korning_3"


def test_previous_snapshot_is_not_overwritten(tmp_path):
    first = _prepare_run_dir(_args(tmp_path / "korning"))
    weights = _yolo_weights(first)
    weights.write_bytes(b"forsta")
    _write_manifest(_args(first), first, _RunState(status="completed"))

    second = _prepare_run_dir(_args(tmp_path / "korning"))
    _yolo_weights(second).write_bytes(b"andra")

    assert weights.read_bytes() == b"forsta"


# --- Absolut sökväg (AC 8) ---


def test_relative_output_becomes_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    resolved = _output_path("traning/korning")

    assert resolved.is_absolute()
    assert resolved == (tmp_path / "traning" / "korning").resolve()


def test_absolute_output_is_kept(tmp_path):
    assert _output_path(str(tmp_path / "korning")) == tmp_path / "korning"


# --- Val av bästa checkpoint (AC 3, 4) ---


def test_yolo_snapshot_is_best_pt(tmp_path):
    weights = _yolo_weights(tmp_path)
    (tmp_path / "yolo" / "weights" / "last.pt").write_bytes(b"senaste")

    assert _best_checkpoint(tmp_path, "yolo") == weights


def test_yolo_without_best_pt_has_no_snapshot(tmp_path):
    (tmp_path / "yolo" / "weights").mkdir(parents=True)
    (tmp_path / "yolo" / "weights" / "last.pt").write_bytes(b"senaste")

    assert _best_checkpoint(tmp_path, "yolo") is None


def test_rfdetr_snapshot_is_checkpoint_best_total(tmp_path):
    best = _rfdetr_weights(tmp_path, "checkpoint_best_total.pth")
    _rfdetr_weights(tmp_path, "last_ema.pth")

    assert _best_checkpoint(tmp_path, "rfdetr") == best


def test_rfdetr_never_picks_last_ema(tmp_path):
    _rfdetr_weights(tmp_path, "last_ema.pth")
    _rfdetr_weights(tmp_path, "last.ckpt")

    assert _best_checkpoint(tmp_path, "rfdetr") is None


def test_rfdetr_falls_back_to_best_ema_while_training(tmp_path):
    """checkpoint_best_total skrivs först när träningen är klar."""
    ema = _rfdetr_weights(tmp_path, "checkpoint_best_ema.pth")
    _rfdetr_weights(tmp_path, "last_ema.pth")

    assert _best_checkpoint(tmp_path, "rfdetr") == ema


def test_rfdetr_prefers_total_over_ema(tmp_path):
    total = _rfdetr_weights(tmp_path, "checkpoint_best_total.pth")
    _rfdetr_weights(tmp_path, "checkpoint_best_ema.pth")

    assert _best_checkpoint(tmp_path, "rfdetr") == total


# --- Manifestet (AC 5, 6, 7) ---


def test_manifest_describes_the_run(tmp_path):
    run_dir = tmp_path / "korning"
    _yolo_weights(run_dir)
    state = _RunState(
        status="completed",
        metrics={"epoch": 10, "total_epochs": 10, "train_loss": 1.2, "map50_95": 0.4},
        epochs_completed=10,
    )

    _write_manifest(_args(run_dir), run_dir, state)

    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["family"] == "yolo"
    assert manifest["base_weights"] == "yolo26n.pt"
    assert manifest["dataset_yaml"] == str(run_dir / "data.yaml")
    assert (manifest["epochs"], manifest["imgsz"], manifest["batch"]) == (10, 640, 16)
    assert manifest["metrics"]["map50_95"] == 0.4
    assert manifest["weights_relative"] == "yolo/weights/best.pt"
    assert manifest["status"] == "completed"
    assert manifest["epochs_completed"] == 10
    assert manifest["started"] is not None
    assert manifest["finished"] is not None
    assert manifest["duration_seconds"] is not None


def test_manifest_points_at_the_rfdetr_snapshot(tmp_path):
    run_dir = tmp_path / "korning"
    _rfdetr_weights(run_dir, "checkpoint_best_total.pth")

    _write_manifest(_args(run_dir, family="rfdetr", weights="rfdetr-small"), run_dir,
                    _RunState(status="completed"))

    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["family"] == "rfdetr"
    assert manifest["weights_relative"] == "rfdetr/checkpoint_best_total.pth"


def test_aborted_run_keeps_the_best_weights_and_manifest(tmp_path):
    """Manifestet skrivs om per epok, så ett avbrott behåller det som fanns."""
    run_dir = tmp_path / "korning"
    _yolo_weights(run_dir)
    _write_manifest(
        _args(run_dir), run_dir,
        _RunState(status="running", metrics={"epoch": 3}, epochs_completed=3),
    )

    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))

    assert manifest["status"] == "running"
    assert manifest["epochs_completed"] == 3
    assert (run_dir / manifest["weights_relative"]).exists()


def test_manifest_is_not_written_without_weights(tmp_path):
    run_dir = tmp_path / "korning"
    run_dir.mkdir()

    _write_manifest(_args(run_dir), run_dir, _RunState())

    assert not (run_dir / MANIFEST_NAME).exists()


# --- Modellväljaren (AC 9) ---


def test_model_selector_lists_every_run(tmp_path):
    trained = tmp_path / "trained"
    for name in ("2026-11-11_120000", "2026-11-12_090000"):
        run_dir = trained / name
        _yolo_weights(run_dir)
        _write_manifest(_args(run_dir), run_dir, _RunState(status="completed"))

    specs = trained_models(trained)

    assert len(specs) == 2
    assert {spec.key for spec in specs} == {
        "trained-2026-11-11_120000",
        "trained-2026-11-12_090000",
    }
    for spec in specs:
        assert Path(spec.weights).exists()


def test_second_run_does_not_hide_the_first(tmp_path):
    trained = tmp_path / "trained"
    first = _prepare_run_dir(_args(trained / "korning"))
    _yolo_weights(first)
    _write_manifest(_args(first), first, _RunState(status="completed"))

    second = _prepare_run_dir(_args(trained / "korning"))
    _yolo_weights(second)
    _write_manifest(_args(second), second, _RunState(status="completed"))

    specs = trained_models(trained)

    assert len(specs) == 2
    assert {Path(spec.weights).parent.parent.parent.name for spec in specs} == {
        "korning",
        "korning_2",
    }
