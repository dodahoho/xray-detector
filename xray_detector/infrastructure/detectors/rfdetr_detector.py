import numpy as np

from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.base import BaseDetector


class RfDetrDetector(BaseDetector):
    def __init__(
        self,
        model_name: str,
        class_names: list[str],
        confidence_threshold: float,
    ) -> None:
        super().__init__(name=f"RF-DETR ({model_name})", class_names=class_names)
        from rfdetr import RFDETRBase

        self.model = RFDETRBase()
        self.confidence_threshold = confidence_threshold

    def detect(self, frame: np.ndarray) -> list[Detection]:
        result = self.model.predict(frame, threshold=self.confidence_threshold)
        detections: list[Detection] = []
        for box in result.get("boxes", []):
            x1, y1, x2, y2 = [float(v) for v in box[:4]]
            class_id = int(box[4]) if len(box) > 4 else 0
            confidence = float(box[5]) if len(box) > 5 else 1.0
            class_name = (
                self.class_names[class_id]
                if 0 <= class_id < len(self.class_names)
                else str(class_id)
            )
            detections.append(
                Detection(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    class_name=class_name,
                    confidence=confidence,
                )
            )
        return detections
