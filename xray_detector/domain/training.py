from dataclasses import dataclass
from datetime import time
from pathlib import Path

from xray_detector.domain.model_input import DEFAULT_SIZE, round_size

#: RF-DETR:s upplösning måste vara delbar med patch_size * num_windows, som är
#: 16 * 2 för alla storlekar (TASK-91).
RFDETR_RESOLUTION_DIVISOR = 32

#: Batch-default per familj (TASK-91). RF-DETR large får OOM på ett 16 GB-kort
#: vid resolution 704 med batch 16, och CUDA-kontexten går inte att rädda efter
#: det, så RF-DETR utgår från en mindre batch.
DEFAULT_BATCH = {"yolo": 16, "rfdetr": 4}

#: Inlärningshastighetens default (TASK-162). Ett dataset under 1000 samples
#: överanpassas snabbt, så träningen utgår från en låg hastighet i stället för
#: ramverkens egna 0.001 respektive 1e-4.
DEFAULT_LEARNING_RATE = 5e-5

#: Nattfönstret: en inställningsnyckel per gräns med värdet "HH:MM", delad av
#: träningsvyn, inställningsdialogen och schemaläggaren (TASK-125).
NIGHT_START_KEY = "training/night_start"
NIGHT_END_KEY = "training/night_end"
NIGHT_START_DEFAULT = time(23, 0)
NIGHT_END_DEFAULT = time(5, 0)


def parse_clock(value: object, fallback: time) -> time:
    """Tolkar "HH:MM" till en tid; ett otydbart värde ger fallback (TASK-125)."""
    try:
        hour, minute = str(value).strip().split(":")
        return time(int(hour), int(minute))
    except (ValueError, AttributeError):
        return fallback


def format_clock(value: time) -> str:
    """Tid som "HH:MM", formatet nattfönstrets inställningar sparas i (TASK-125)."""
    return value.strftime("%H:%M")


def imgsz_for(width: int, height: int) -> int:
    """Bildstorlek som bevarar datasetets upplösning (TASK-80).

    Träningen tar en enda storlek och letterboxar till en kvadrat, så den
    längsta sidan väljs: då ryms hela bilden utan att något skalas ned.
    """
    return round_size(max(int(width), int(height)))


def default_batch(family: str) -> int:
    """Batch-default för modellfamiljen."""
    return DEFAULT_BATCH.get(family, DEFAULT_BATCH["yolo"])


def rfdetr_resolution_error(imgsz: int) -> str | None:
    """Felmeddelande när bildstorleken inte går att använda som RF-DETR-upplösning.

    RF-DETR delar bilden i patchar om patch_size pixlar och väver dem över
    num_windows fönster, så upplösningen måste vara delbar med 32. Felet
    returneras i stället för att kastas, så både träningsprocessen och vyn kan
    avvisa storleken innan träningen startar.
    """
    if imgsz <= 0:
        return f"Bildstorleken måste vara positiv, fick {imgsz}"
    if imgsz % RFDETR_RESOLUTION_DIVISOR:
        return (
            f"RF-DETR kräver en bildstorlek som är delbar med "
            f"{RFDETR_RESOLUTION_DIVISOR} (patch_size 16 x num_windows 2), "
            f"fick {imgsz}"
        )
    return None


def trained_model_name(
    base_name: str,
    date: str,
    pairs: int,
    synthetic: int,
    classes: int,
) -> str:
    """Visningsnamn för en tränad modell (TASK-108).

    Mönstret är ``[basmodell] [datum] [ursprungsbildpar + syntetiska bildpar]
    bildpar [antal klasser]``, till exempel ``YOLO26 large 2026-11-15 13+29
    bildpar 4 klasser``. Basmodellens namn är modellen den första träningen
    utgick från, så en vidareträning på samma dataset bara byter datum.
    """
    klass = "klass" if classes == 1 else "klasser"
    return f"{base_name} {date} {pairs}+{synthetic} bildpar {classes} {klass}"


@dataclass
class TrainConfig:
    weights: str
    output_dir: Path
    #: sätts när datasetexporten är klar, alltså strax före start (TASK-151)
    dataset_yaml: Path | None = None
    epochs: int = 100
    imgsz: int = DEFAULT_SIZE
    batch: int | None = None
    #: inlärningshastighet, justerbar i träningsvyn (TASK-162)
    learning_rate: float = DEFAULT_LEARNING_RATE
    family: str = "yolo"
    overfitting_guard: bool = True
    #: visningsnamn för den tränade modellen (TASK-108)
    name: str = ""
    #: basmodellens visningsnamn, ärvt när basen är en egen tränad modell (TASK-108)
    base_name: str = ""

    def batch_size(self) -> int:
        """Batchestorleken; familjens default när inget eget värde är satt."""
        return default_batch(self.family) if self.batch is None else int(self.batch)


@dataclass(frozen=True)
class EpochMetrics:
    """Epokvisa träningsvärden som träningsprocessen rapporterar (TASK-44).

    Fälten är gemensamma för YOLO och RF-DETR. Ett värde som familjen inte
    rapporterar är None, så GUI:t kan visa det som saknas i stället för noll.
    """

    epoch: int
    total_epochs: int
    train_loss: float | None = None
    val_loss: float | None = None
    map50: float | None = None
    map50_95: float | None = None
    precision: float | None = None
    recall: float | None = None

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "epoch": self.epoch,
            "total_epochs": self.total_epochs,
            "train_loss": self.train_loss,
            "val_loss": self.val_loss,
            "map50": self.map50,
            "map50_95": self.map50_95,
            "precision": self.precision,
            "recall": self.recall,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "EpochMetrics":
        """Bygger eventet ur ett JSON-objekt; saknade fält blir None."""
        return cls(
            epoch=int(payload["epoch"]),
            total_epochs=int(payload["total_epochs"]),
            train_loss=_optional_float(payload.get("train_loss")),
            val_loss=_optional_float(payload.get("val_loss")),
            map50=_optional_float(payload.get("map50")),
            map50_95=_optional_float(payload.get("map50_95")),
            precision=_optional_float(payload.get("precision")),
            recall=_optional_float(payload.get("recall")),
        )

    def summary(self) -> str:
        """Läsbar rad för träningsloggen."""
        parts = [f"Epok {self.epoch}/{self.total_epochs}"]
        for label, value in (
            ("train-loss", self.train_loss),
            ("val-loss", self.val_loss),
            ("mAP50", self.map50),
            ("mAP50-95", self.map50_95),
            ("precision", self.precision),
            ("recall", self.recall),
        ):
            if value is not None:
                parts.append(f"{label} {value:.4f}")
        return "  ".join(parts)


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


#: En heartbeat som är äldre än så här rapporterar ingen pågående träning (TASK-96).
PROGRESS_STALE_AFTER_S = 10.0


@dataclass(frozen=True)
class ProgressEvent:
    """Hur långt träningsprocessen kommit inom pågående epok (TASK-96).

    Epokeventet kommer först när epoken är klar, så en epok som tar flera
    minuter ser ut som en hängning. Det här eventet skickas med jämna mellanrum
    under epoken och bär sin egen tidsstämpel, så mottagaren kan avgöra om
    rapporten fortfarande är aktuell.
    """

    epoch: int
    step: int
    total_steps: int
    updated: float

    @property
    def fraction(self) -> float:
        return self.step / self.total_steps if self.total_steps > 0 else 0.0

    def age(self, now: float) -> float:
        """Sekunder sedan träningsprocessen skrev eventet."""
        return max(0.0, now - self.updated)

    def is_stale(self, now: float, max_age: float = PROGRESS_STALE_AFTER_S) -> bool:
        """Sant när ingen ny rapport kommit på max_age sekunder."""
        return self.age(now) > max_age

    def as_dict(self) -> dict[str, float | int]:
        return {
            "epoch": self.epoch,
            "step": self.step,
            "total_steps": self.total_steps,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ProgressEvent":
        return cls(
            epoch=int(payload["epoch"]),
            step=int(payload["step"]),
            total_steps=int(payload["total_steps"]),
            updated=float(payload["updated"]),
        )

    def summary(self) -> str:
        """Läsbar rad för träningsvyn."""
        percent = round(self.fraction * 100)
        return f"Epok {self.epoch} · steg {self.step}/{self.total_steps} ({percent} %)"
