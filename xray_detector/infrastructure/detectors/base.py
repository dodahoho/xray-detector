from abc import ABC, abstractmethod
from collections.abc import Iterable

import numpy as np

from xray_detector.domain.detection import Detection


def class_names_from(names, source: str) -> list[str]:
    """Modellens egna klassnamn som en indexordnad lista (TASK-52).

    Ultralytics ger {index: namn} och rfdetr en lista. Saknas namnen går
    klasserna inte att namnge, och då är ett tydligt fel bättre än att
    overlayn visar index.
    """
    if isinstance(names, dict):
        names = [names[index] for index in sorted(names)]
    if not names:
        raise ValueError(f"Kunde inte läsa klassnamnen ur {source}")
    return [str(name) for name in names]


class BaseDetector(ABC):
    """Gemensamt gränssnitt för detektorerna.

    class_names är modellens egna klassnamn, lästa ur vikterna när detektorn
    laddas (TASK-52). AppConfig.classes beskriver datasetets etiketter och är
    en annan lista.
    """

    def __init__(self, name: str, class_names: list[str]) -> None:
        self.name = name
        self.class_names = class_names
        self.enabled_classes: set[str] | None = None
        self.confidence_threshold = 0.4

    def set_confidence_threshold(self, value: float) -> None:
        """Ändrar tröskeln utan att modellen laddas om (TASK-36)."""
        self.confidence_threshold = value

    def set_enabled_classes(self, class_names: Iterable[str] | None) -> None:
        """Klasserna som ska visas; None betyder alla (TASK-53)."""
        self.enabled_classes = None if class_names is None else set(class_names)

    def filter_detections(self, detections: list[Detection]) -> list[Detection]:
        """Tar bort klasser som användaren valt bort i detektionsvyn (TASK-53)."""
        if self.enabled_classes is None:
            return detections
        return [
            detection
            for detection in detections
            if detection.class_name in self.enabled_classes
        ]

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]: ...
