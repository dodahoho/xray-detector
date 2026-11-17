import threading
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


def cuda_device_label() -> str:
    """Enhetsbeskrivning för logg och GUI (TASK-101)."""
    import torch

    if not torch.cuda.is_available():
        return "CPU (CUDA ej tillgänglig)"
    try:
        name = torch.cuda.get_device_name(0)
    except Exception:
        name = "GPU"
    return f"CUDA ({name})"


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
        # Samma detektor delas av två strömtrådar och styrs från GUI-tråden, så
        # både modellanropet och de två inställningarna går genom ett lås
        # (TASK-128). RLock eftersom detect() anropar filter_detections().
        self._lock = threading.RLock()

    def set_confidence_threshold(self, value: float) -> None:
        """Ändrar tröskeln utan att modellen laddas om (TASK-36)."""
        with self._lock:
            self.confidence_threshold = value

    def set_enabled_classes(self, class_names: Iterable[str] | None) -> None:
        """Klasserna som ska visas; None betyder alla (TASK-53)."""
        with self._lock:
            self.enabled_classes = None if class_names is None else set(class_names)

    def filter_detections(self, detections: list[Detection]) -> list[Detection]:
        """Tar bort klasser som användaren valt bort i detektionsvyn (TASK-53)."""
        with self._lock:
            if self.enabled_classes is None:
                return detections
            return [
                detection
                for detection in detections
                if detection.class_name in self.enabled_classes
            ]

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Kör modellen under lås, ett anrop i taget (TASK-128).

        Ultralytics och rfdetr är inte trådsäkra på samma instans, och två
        strömtrådar delar en detektor. Anropen serialiseras därför här i
        stället för att varje anropare behöva komma ihåg ett lås.
        """
        with self._lock:
            return self._detect(frame)

    @abstractmethod
    def _detect(self, frame: np.ndarray) -> list[Detection]: ...
