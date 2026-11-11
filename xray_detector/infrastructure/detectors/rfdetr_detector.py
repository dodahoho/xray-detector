from pathlib import Path

import cv2
import numpy as np

from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.base import BaseDetector

#: Modellnyckel -> rfdetr-klass. rfdetr 1.7 ersatte RFDETRBase med
#: storleksspecifika klasser (se rfdetrs migreringsguide).
RFDETR_VARIANTS = {
    "rfdetr-nano": "RFDETRNano",
    "rfdetr-small": "RFDETRSmall",
    "rfdetr-medium": "RFDETRMedium",
    "rfdetr-large": "RFDETRLarge",
}


def rfdetr_variant(model_name: str):
    """Returnerar rfdetr-klassen för en modellnyckel, t.ex. 'rfdetr-small'."""
    import rfdetr

    class_name = RFDETR_VARIANTS.get(model_name)
    if class_name is None:
        raise ValueError(f"Okänd RF-DETR-modell: {model_name}")
    return getattr(rfdetr, class_name)


def _is_checkpoint(weights: str) -> bool:
    """Sant när vikterna är en sparad fil i stället för en storleksnyckel."""
    return Path(weights).is_file()


def _load_model(weights: str):
    """Publicerad storlek (modellnyckel) eller tränad snapshot (sökväg till .pth).

    En tränad snapshot bär både arkitektur och antal klasser, så
    from_checkpoint väljer variant och läser detektionshuvudet ur filen.
    """
    import rfdetr

    if _is_checkpoint(weights):
        return rfdetr.from_checkpoint(weights)
    return rfdetr_variant(weights)()


class RfDetrDetector(BaseDetector):
    """RF-DETR-backend (valfritt rfdetr-paket).

    predict() returnerar supervision.Detections med xyxy/class_id/confidence
    och modellens egna klassnamn i data["class_name"].
    """

    def __init__(
        self,
        weights: str,
        class_names: list[str],
        confidence_threshold: float,
    ) -> None:
        label = Path(weights).stem if _is_checkpoint(weights) else weights
        super().__init__(name=f"RF-DETR ({label})", class_names=class_names)
        from xray_detector.infrastructure.detectors.tuning import (
            configure_inference_threads,
        )

        configure_inference_threads()
        self.model = _load_model(weights)
        self._optimize_for_inference()
        self.confidence_threshold = confidence_threshold

    def _optimize_for_inference(self) -> None:
        """FP16-optimering på GPU ger cirka 60 % snabbare inferens (TASK-36).

        rfdetr varnar i loggen när modellen inte är optimerad. Optimeringen
        är en hastighetsvinst, inte ett krav: misslyckas den fortsätter
        modellen ooptimerad och rfdetr varnar som vanligt.
        """
        import torch

        if not torch.cuda.is_available():
            return
        try:
            self.model.inference(dtype=torch.float16)
        except Exception:
            pass

    def detect(self, frame: np.ndarray) -> list[Detection]:
        # rfdetr vantar RGB; ramarna fran OpenCV ar BGR
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.model.predict(rgb, threshold=self.confidence_threshold)
        names = result.data.get("class_name")
        detections: list[Detection] = []
        for index, (x1, y1, x2, y2) in enumerate(result.xyxy):
            class_id = int(result.class_id[index]) if result.class_id is not None else 0
            confidence = (
                float(result.confidence[index])
                if result.confidence is not None
                else 1.0
            )
            detections.append(
                Detection(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    class_name=self._class_name(names, index, class_id),
                    confidence=confidence,
                )
            )
        return detections

    def _class_name(self, names, index: int, class_id: int) -> str:
        """Modellens eget klassnamn, annars appens klasslista, annars id:t."""
        if names is not None and index < len(names) and names[index]:
            return str(names[index])
        if 0 <= class_id < len(self.class_names):
            return self.class_names[class_id]
        return str(class_id)
