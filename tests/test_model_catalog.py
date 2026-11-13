"""Modellistan i models/models.json (TASK-81)."""

import json
import urllib.request
from pathlib import Path

import pytest

from xray_detector.application.model_registry import (
    CATALOG_NAME,
    CATALOG_VERSION,
    MODEL_SPECS,
    ModelCatalog,
    ModelSpec,
    base_models,
)


def _catalog(tmp_path: Path) -> ModelCatalog:
    return ModelCatalog(tmp_path / "models")


def _weights(tmp_path: Path, name: str = "egen.pt") -> Path:
    path = tmp_path / name
    path.write_bytes(b"vikter")
    return path


class _FakeResponse:
    """Svar från urlopen utan nätverk."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


# --- Katalogen (AC 1) ---


def test_catalog_falls_back_to_the_standard_list(tmp_path):
    catalog = _catalog(tmp_path)

    assert catalog.specs() == MODEL_SPECS
    assert not catalog.path.exists(), "standardlistan skrivs först när den ändras"


def test_catalog_is_written_when_the_list_changes(tmp_path):
    catalog = _catalog(tmp_path)

    catalog.add_local(_weights(tmp_path))

    payload = json.loads(catalog.path.read_text(encoding="utf-8"))
    assert payload["version"] == CATALOG_VERSION
    assert [entry["key"] for entry in payload["models"]] == [
        *(spec.key for spec in MODEL_SPECS),
        "egen",
    ]


def test_catalog_reads_the_saved_list(tmp_path):
    catalog = _catalog(tmp_path)
    saved = [ModelSpec("egen", "Egen modell", "yolo", "egen.pt")]
    catalog.save(saved)

    assert _catalog(tmp_path).specs() == saved


def test_empty_catalog_stays_empty(tmp_path):
    """En tom lista är ett giltigt val, inte ett skäl att återgå till standard."""
    catalog = _catalog(tmp_path)
    catalog.save([])

    assert _catalog(tmp_path).specs() == []


def test_broken_catalog_falls_back_to_the_standard_list(tmp_path):
    catalog = _catalog(tmp_path)
    catalog.models_dir.mkdir(parents=True)
    catalog.path.write_text("{ inte json", encoding="utf-8")

    assert catalog.specs() == MODEL_SPECS


def test_catalog_skips_incomplete_entries(tmp_path):
    catalog = _catalog(tmp_path)
    catalog.models_dir.mkdir(parents=True)
    catalog.path.write_text(
        json.dumps(
            {
                "version": CATALOG_VERSION,
                "models": [
                    {"key": "hel", "label": "Hel", "family": "yolo", "weights": "hel.pt"},
                    {"key": "utan-familj", "label": "Utan familj", "weights": "x.pt"},
                    {"key": "okand", "label": "Okänd", "family": "annat", "weights": "x.pt"},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert [spec.key for spec in catalog.specs()] == ["hel"]


# --- Lägga till från fil (AC 3) ---


def test_add_local_copies_the_weights_into_models_dir(tmp_path):
    catalog = _catalog(tmp_path)
    source = _weights(tmp_path, "min-modell.pt")

    spec = catalog.add_local(source)

    assert (catalog.models_dir / "min-modell.pt").read_bytes() == b"vikter"
    assert spec == ModelSpec("min-modell", "min-modell", "yolo", "min-modell.pt")
    assert spec in catalog.specs()


def test_add_local_keeps_an_existing_weight_file(tmp_path):
    """En vikt som redan ligger i models/ skrivs aldrig över."""
    catalog = _catalog(tmp_path)
    catalog.models_dir.mkdir(parents=True)
    (catalog.models_dir / "min-modell.pt").write_bytes(b"gammal")

    spec = catalog.add_local(_weights(tmp_path, "min-modell.pt"))

    assert (catalog.models_dir / "min-modell.pt").read_bytes() == b"gammal"
    assert spec.weights == "min-modell_2.pt"
    assert (catalog.models_dir / "min-modell_2.pt").read_bytes() == b"vikter"


def test_add_local_takes_the_family_from_the_suffix(tmp_path):
    catalog = _catalog(tmp_path)

    spec = catalog.add_local(_weights(tmp_path, "rfdetr-egen.pth"))

    assert spec.family == "rfdetr"


def test_add_local_rejects_an_unknown_weight_type(tmp_path):
    catalog = _catalog(tmp_path)

    with pytest.raises(ValueError, match="Okänd vikttyp: modell.onnx"):
        catalog.add_local(_weights(tmp_path, "modell.onnx"))


def test_add_local_rejects_a_missing_file(tmp_path):
    catalog = _catalog(tmp_path)

    with pytest.raises(ValueError, match="Filen finns inte"):
        catalog.add_local(tmp_path / "saknas.pt")


def test_added_models_get_a_unique_key(tmp_path):
    catalog = _catalog(tmp_path)

    first = catalog.add_local(_weights(tmp_path, "a.pt"), label="Min modell")
    second = catalog.add_local(_weights(tmp_path, "b.pt"), label="Min modell")

    assert (first.key, second.key) == ("min-modell", "min-modell-2")


# --- Lägga till från internet (AC 4) ---


def test_add_from_url_downloads_into_models_dir(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path)
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda url, timeout: _FakeResponse(b"nedladdad")
    )

    spec = catalog.add_from_url("https://example.com/vikter/egen-modell.pt")

    assert (catalog.models_dir / "egen-modell.pt").read_bytes() == b"nedladdad"
    assert spec == ModelSpec("egen-modell", "egen-modell", "yolo", "egen-modell.pt")
    assert spec in catalog.specs()


def test_add_from_url_rejects_an_address_without_a_weight_file(tmp_path):
    catalog = _catalog(tmp_path)

    with pytest.raises(ValueError, match="pekar inte på en viktfil"):
        catalog.add_from_url("https://example.com/vikter/")


# --- Ta bort och byta namn (AC 5, 6) ---


def test_remove_takes_the_model_out_of_the_list_and_keeps_the_file(tmp_path):
    catalog = _catalog(tmp_path)
    spec = catalog.add_local(_weights(tmp_path, "min-modell.pt"))

    catalog.remove(spec.key)

    assert spec not in catalog.specs()
    assert (catalog.models_dir / "min-modell.pt").exists(), "filen ligger kvar"


def test_rename_changes_the_label_but_not_the_key(tmp_path):
    catalog = _catalog(tmp_path)
    spec = catalog.add_local(_weights(tmp_path, "min-modell.pt"))

    catalog.rename(spec.key, "  Vår bästa modell  ")

    renamed = next(item for item in catalog.specs() if item.key == spec.key)
    assert renamed.label == "Vår bästa modell"
    assert renamed.weights == spec.weights


def test_rename_rejects_an_empty_label(tmp_path):
    catalog = _catalog(tmp_path)

    with pytest.raises(ValueError, match="får inte vara tomt"):
        catalog.rename("yolo26m", "   ")


# --- Väljarnas lista (AC 1, 7) ---


def test_base_models_resolve_weight_files_under_models_dir(tmp_path):
    catalog = _catalog(tmp_path)
    catalog.save([ModelSpec("egen", "Egen", "yolo", "egen.pt")])

    specs = base_models(catalog.models_dir)

    assert specs[0].weights == str(catalog.models_dir / "egen.pt")


def test_base_models_keep_rfdetr_size_names(tmp_path):
    catalog = _catalog(tmp_path)
    catalog.save([ModelSpec("rfdetr-nano", "RF-DETR nano", "rfdetr", "rfdetr-nano")])

    assert base_models(catalog.models_dir)[0].weights == "rfdetr-nano"


def test_catalog_name_is_models_json(tmp_path):
    assert _catalog(tmp_path).path.name == CATALOG_NAME == "models.json"
