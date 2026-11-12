from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrainConfig:
    dataset_yaml: Path
    weights: str
    output_dir: Path
    epochs: int = 100
    imgsz: int = 640
    batch: int = 16
    family: str = "yolo"
    overfitting_guard: bool = True


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
