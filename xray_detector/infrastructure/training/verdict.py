"""Dom över hur en träning slutade (TASK-97).

Historikvyn visar mAP, epoker och status, men inte om kurvan planade ut, om
modellen övertränade eller om träningen helt enkelt var för kort — vilket är
det man behöver veta för att välja nästa steg. Domen räknas fram ur körningens
sparade epokvärden, så den går att få fram även för en körning som gjordes
innan funktionen fanns.
"""

from dataclasses import dataclass

from xray_detector.domain.training import EpochMetrics

#: Färre epoker än så här går inte att bedöma.
MIN_EPOCHS = 5
#: Minsta mAP-vinst över det sista fönstret som räknas som en förbättring.
MIN_GAIN = 0.005

IMPROVING = "improving"
OVERFITTING = "overfitting"
PLATEAUED = "plateaued"
UNKNOWN = "unknown"

VERDICT_LABELS = {
    IMPROVING: "Förbättras",
    OVERFITTING: "Övertränad",
    PLATEAUED: "Avstannad",
    UNKNOWN: "-",
}


@dataclass(frozen=True)
class Verdict:
    """Körningens dom: en kort etikett och en förklaring med råd."""

    kind: str
    text: str

    @property
    def label(self) -> str:
        return VERDICT_LABELS.get(self.kind, self.kind)


def _score(metrics: EpochMetrics) -> float | None:
    """Värdet domen bygger på: mAP50-95, annars mAP50."""
    if metrics.map50_95 is not None:
        return metrics.map50_95
    if metrics.map50 is not None:
        return metrics.map50
    return None


def _difference(first: float | None, second: float | None) -> float | None:
    if first is None or second is None:
        return None
    return first - second


def verdict(epochs: list[EpochMetrics]) -> Verdict:
    """Klassar en avslutad körning som förbättras, övertränad eller avstannad.

    En kurva som planar ut har sin bästa epok sist, så "bäst är nyligen" räcker
    inte som kriterium: det krävs också en mätbar vinst över det sista
    fönstret. Överträning kräver att train-loss föll medan val-loss steg efter
    den bästa epoken; enbart en avstannad utveckling räknas som avstannad.
    """
    scored = [(metrics, _score(metrics)) for metrics in epochs]
    scored = [(metrics, score) for metrics, score in scored if score is not None]
    if len(scored) < MIN_EPOCHS:
        return Verdict(UNKNOWN, f"för få epoker att bedöma ({len(scored)})")

    best_index = max(range(len(scored)), key=lambda index: scored[index][1])
    best, best_score = scored[best_index]
    last, last_score = scored[-1]
    window = max(3, len(scored) // 10)
    tail = len(scored) - 1 - best_index
    gain = last_score - scored[-window][1]

    if tail <= window and gain > MIN_GAIN:
        return Verdict(
            IMPROVING,
            f"fortsätter förbättras: bäst mAP50-95 {best_score:.4f} i epok "
            f"{best.epoch} av {last.epoch}, {gain:+.4f} över de sista {window} "
            f"epokerna. Öka antalet epoker innan något annat ändras.",
        )

    train_drop = _difference(best.train_loss, last.train_loss)
    val_rise = _difference(last.val_loss, best.val_loss)
    if train_drop is not None and val_rise is not None and train_drop > 0 and val_rise > 0:
        return Verdict(
            OVERFITTING,
            f"övertränad: efter epok {best.epoch} föll train-loss {train_drop:.3f} "
            f"medan val-loss steg {val_rise:.3f}. Byt till en mindre modellstorlek "
            f"eller öka augmentationen.",
        )

    return Verdict(
        PLATEAUED,
        f"avstannad: bäst mAP50-95 {best_score:.4f} i epok {best.epoch} av "
        f"{last.epoch}, bara {gain:+.4f} över de sista {window} epokerna. "
        f"Prova en större modellstorlek eller högre upplösning.",
    )
