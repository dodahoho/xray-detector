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


class RfDetrDetector(BaseDetector):
    """RF-DETR-backend (valfritt rfdetr-paket).

    predict() returnerar supervision.Detections med xyxy/class_id/confidence
    och modellens egna klassnamn i data["class_name"].
    """

    def __init__(
        self,
        model_name: str,
        class_names: list[str],
        confidence_threshold: float,
    ) -> None:
        super().__init__(name=f"RF-DETR ({model_name})", class_names=class_names)
        self.model = rfdetr_variant(model_name)()
        self.confidence_threshold = confidence_threshold

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
