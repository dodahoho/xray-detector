"""Modellistan och detektorerna bakom den (TASK-50, TASK-81).

Standardmodellerna ligger i MODEL_SPECS, men listan ägs av models/models.json
när filen finns: användaren lägger till, byter namn på och tar bort modeller i
de globala inställningarna, och då skrivs filen. Vikterna anges relativt
models_dir, så listan följer med när katalogen pekas om i config.yaml.
"""

import shutil
import urllib.request
from dataclasses import asdict, dataclass, replace
from json import load as json_load
from pathlib import Path
from urllib.parse import urlparse

from xray_detector.infrastructure.dataset_store.json_io import atomic_write_json
from xray_detector.infrastructure.detectors.base import BaseDetector

CATALOG_NAME = "models.json"
CATALOG_VERSION = 1
# viktfilens ändelse avgör vilken detektor som laddar den
FAMILY_BY_SUFFIX = {".pt": "yolo", ".pth": "rfdetr"}
FAMILIES = tuple(FAMILY_BY_SUFFIX.values())
DOWNLOAD_TIMEOUT_S = 60


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    family: str
    weights: str


MODEL_SPECS: list[ModelSpec] = [
    ModelSpec("yolo26n", "YOLO26 nano", "yolo", "yolo26n.pt"),
    ModelSpec("yolo26s", "YOLO26 small", "yolo", "yolo26s.pt"),
    ModelSpec("yolo26m", "YOLO26 medium", "yolo", "yolo26m.pt"),
    ModelSpec("rfdetr-nano", "RF-DETR nano", "rfdetr", "rfdetr-nano"),
    ModelSpec("rfdetr-small", "RF-DETR small", "rfdetr", "rfdetr-small"),
    ModelSpec("rfdetr-medium", "RF-DETR medium", "rfdetr", "rfdetr-medium"),
    ModelSpec("rfdetr-large", "RF-DETR large", "rfdetr", "rfdetr-large"),
]


def family_for(path: Path) -> str | None:
    """Modellfamiljen ur viktfilens ändelse; None för en okänd typ."""
    return FAMILY_BY_SUFFIX.get(Path(path).suffix.lower())


def _resolve_weights(weights: str, models_dir: Path) -> str:
    """Viktfiler ligger under models_dir; RF-DETR:s storleksnamn lämnas orörda."""
    if family_for(Path(weights)) is None:
        return weights
    return str(Path(models_dir) / weights)


def _slug(text: str) -> str:
    """Nyckel ur ett visningsnamn: gemener, bindestreck i stället för mellanslag."""
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return "-".join(part for part in cleaned.split("-") if part) or "modell"


def _unique_key(label: str, taken: set[str]) -> str:
    base = _slug(label)
    key = base
    index = 2
    while key in taken:
        key = f"{base}-{index}"
        index += 1
    return key


def _spec_from_entry(entry) -> ModelSpec | None:
    """En post ur models.json; None när posten inte är en komplett modell."""
    if not isinstance(entry, dict):
        return None
    try:
        key = str(entry["key"])
        label = str(entry["label"])
        family = str(entry["family"])
        weights = str(entry["weights"])
    except KeyError:
        return None
    if not key or not label or family not in FAMILIES:
        return None
    return ModelSpec(key=key, label=label, family=family, weights=weights)


class ModelCatalog:
    """Användarens modellista i models/models.json (TASK-81).

    Filen är källan när den finns; annars gäller MODEL_SPECS och filen skrivs
    först när listan ändras. En trasig fil faller tillbaka på standardlistan i
    stället för att appen startar utan modeller.
    """

    def __init__(self, models_dir: Path) -> None:
        self.models_dir = Path(models_dir)
        self.path = self.models_dir / CATALOG_NAME

    def specs(self) -> list[ModelSpec]:
        """Modellerna i listan; standardlistan när filen saknas eller är trasig."""
        entries = self._read()
        return list(MODEL_SPECS) if entries is None else entries

    def save(self, specs: list[ModelSpec]) -> None:
        atomic_write_json(
            self.path,
            {"version": CATALOG_VERSION, "models": [asdict(spec) for spec in specs]},
        )

    def add_local(self, source: Path, label: str | None = None) -> ModelSpec:
        """Kopierar en viktfil till models_dir och lägger till den i listan."""
        source = Path(source)
        family = family_for(source)
        if family is None:
            raise ValueError(f"Okänd vikttyp: {source.name}")
        if not source.is_file():
            raise ValueError(f"Filen finns inte: {source}")
        target = self._free_path(source.name)
        shutil.copy2(source, target)
        return self._append(target.name, label or source.stem, family)

    def add_from_url(self, url: str, label: str | None = None) -> ModelSpec:
        """Laddar ner en viktfil till models_dir och lägger till den i listan."""
        name = Path(urlparse(url).path).name
        family = family_for(Path(name))
        if family is None:
            raise ValueError(f"Adressen pekar inte på en viktfil: {url}")
        target = self._free_path(name)
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as response:
            target.write_bytes(response.read())
        return self._append(target.name, label or Path(name).stem, family)

    def remove(self, key: str) -> None:
        """Tar bort modellen ur listan; viktfilen ligger kvar i models_dir."""
        self.save([spec for spec in self.specs() if spec.key != key])

    def rename(self, key: str, label: str) -> None:
        """Byter visningsnamn; nyckeln och viktfilen är oförändrade."""
        label = label.strip()
        if not label:
            raise ValueError("Visningsnamnet får inte vara tomt")
        self.save(
            [
                replace(spec, label=label) if spec.key == key else spec
                for spec in self.specs()
            ]
        )

    def _read(self) -> list[ModelSpec] | None:
        if not self.path.exists():
            return None
        try:
            with open(self.path, encoding="utf-8") as file:
                payload = json_load(file)
        except (OSError, ValueError):
            return None
        entries = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return None
        specs = []
        for entry in entries:
            spec = _spec_from_entry(entry)
            if spec is not None:
                specs.append(spec)
        return specs

    def _append(self, weights: str, label: str, family: str) -> ModelSpec:
        specs = self.specs()
        spec = ModelSpec(
            key=_unique_key(label, {existing.key for existing in specs}),
            label=label,
            family=family,
            weights=weights,
        )
        self.save([*specs, spec])
        return spec

    def _free_path(self, name: str) -> Path:
        """Ledig sökväg under models_dir; en befintlig vikt skrivs aldrig över."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        target = self.models_dir / name
        index = 2
        while target.exists():
            target = self.models_dir / f"{Path(name).stem}_{index}{Path(name).suffix}"
            index += 1
        return target


def create_detector(
    spec: ModelSpec,
    confidence_threshold: float,
) -> BaseDetector:
    """Skapar detektorn för en modell; klassnamnen läses ur modellen (TASK-52)."""
    if spec.family == "yolo":
        from xray_detector.infrastructure.detectors.yolo_detector import YoloDetector

        return YoloDetector(spec.weights, confidence_threshold)
    if spec.family == "rfdetr":
        from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector

        return RfDetrDetector(spec.weights, confidence_threshold)
    raise ValueError(f"Okänd modellfamilj: {spec.family}")


def spec_by_key(key: str) -> ModelSpec:
    for spec in MODEL_SPECS:
        if spec.key == key:
            return spec
    raise ValueError(f"Okänd modell: {key}")


def base_models(models_dir: Path) -> list[ModelSpec]:
    """Modellerna i listan med YOLO-vikterna under models_dir (TASK-50, TASK-81).

    Ultralytics laddar ner en saknad vikt till den sökväg den får, så
    basvikterna hamnar i models/ i stället för i arbetskatalogen. RF-DETR
    bygger modellen ur paketet och behåller därför sitt storleksnamn.
    """
    return [
        replace(spec, weights=_resolve_weights(spec.weights, models_dir))
        for spec in ModelCatalog(models_dir).specs()
    ]


def trained_models(trained_dir: Path) -> list[ModelSpec]:
    """Listar egentränade modeller utifrån training_manifest.json under models/trained/.

    Sökningen är rekursiv så att varje träningskörnings egen katalog
    hittas för sig.
    """
    trained_dir = Path(trained_dir)
    specs: list[ModelSpec] = []
    for manifest_path in sorted(trained_dir.rglob("training_manifest.json")):
        try:
            with open(manifest_path, encoding="utf-8") as file:
                manifest = json_load(file)
            weights = manifest_path.parent / manifest.get("weights_relative", "")
            if not weights.exists():
                continue
            run_dir = manifest_path.parent.relative_to(trained_dir).as_posix()
        except (OSError, ValueError):
            continue
        base = Path(manifest.get("base_weights", "modell")).stem
        classes = ", ".join(manifest.get("classes", []))
        label = f"Tränad {run_dir} ({base})" + (f" [{classes}]" if classes else "")
        # manifest utan familj är skrivna före TASK-48 och är alltid YOLO
        family = str(manifest.get("family") or "yolo")
        specs.append(
            ModelSpec(key=f"trained-{run_dir}", label=label,
                      family=family, weights=str(weights))
        )
    return specs


def device_status() -> tuple[str, str]:
    """Returnerar (statusText, CSS-färg) för enhetsindikatorn i GUI:t."""
    try:
        import torch

        if torch.cuda.is_available():
            return f"Enhet: CUDA ({torch.cuda.get_device_name(0)})", "#2a8"
        return "Enhet: CPU (CUDA ej tillgänglig)", "#c33"
    except ImportError:
        return "Enhet: PyTorch saknas", "#c33"
