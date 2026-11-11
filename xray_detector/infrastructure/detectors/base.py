from abc import ABC, abstractmethod

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
        self.confidence_threshold = 0.4

    def set_confidence_threshold(self, value: float) -> None:
        """Ändrar tröskeln utan att modellen laddas om (TASK-36)."""
        self.confidence_threshold = value

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]: ...
