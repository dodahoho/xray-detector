"""Överträningsdetektion för träningsprocessen (TASK-46).

Ultralytics patience och RF-DETR:s early stopping mäter utebliven förbättring
av valvärdet. Överträning är något annat: train-loss fortsätter ner medan
val-mAP vänder ner. Vakten jämför därför valvärdet med train-loss och larmar
först när båda rör sig åt det hållet.
"""

from xray_detector.domain.training import EpochMetrics

DEFAULT_PATIENCE = 10
DEFAULT_MIN_DELTA = 0.001


def _score(metrics: EpochMetrics) -> float | None:
    """Värdet som ska förbättras: mAP om det finns, annars negativ val-loss."""
    if metrics.map50_95 is not None:
        return metrics.map50_95
    if metrics.map50 is not None:
        return metrics.map50
    if metrics.val_loss is not None:
        return -metrics.val_loss
    return None


class OverfittingGuard:
    """Larmar när valvärdet stått still för länge medan train-loss sjunker.

    patience är antalet epoker utan förbättring innan vakten prövar. Larmet
    kräver dessutom att train-loss är lägre än vid den bästa epoken, så en
    enbart avstannad utveckling räknas som avstannad, inte som överträning.
    """

    def __init__(
        self,
        patience: int = DEFAULT_PATIENCE,
        min_delta: float = DEFAULT_MIN_DELTA,
    ) -> None:
        self.patience = max(1, int(patience))
        self.min_delta = float(min_delta)
        self.reason: str | None = None
        self._best_score: float | None = None
        self._best_epoch = 0
        self._best_train_loss: float | None = None

    def update(self, metrics: EpochMetrics) -> str | None:
        """Matar in en epok; returnerar orsaken första gången vakten larmar."""
        if self.reason is not None:
            return self.reason
        score = _score(metrics)
        if score is None:
            return None
        if self._best_score is None or score > self._best_score + self.min_delta:
            self._best_score = score
            self._best_epoch = metrics.epoch
            self._best_train_loss = metrics.train_loss
            return None
        if metrics.epoch - self._best_epoch < self.patience:
            return None
        if metrics.train_loss is None or self._best_train_loss is None:
            return None
        if metrics.train_loss >= self._best_train_loss - self.min_delta:
            return None
        self.reason = (
            f"Överträning: valvärdet har inte förbättrats sedan epok "
            f"{self._best_epoch} medan train-loss fortsätter att sjunka"
        )
        return self.reason
