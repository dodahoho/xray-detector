"""Tidsmässig utjämning av detektioner mellan ramar (TASK-33).

Modellen ger små variationer i rutans position och storlek från ram till
ram, och en detektion nära confidence-tröskeln kan slå av och på. Utan
utjämning upplevs overlayn som ryckig. Här matchas varje detektion mot en
spårad ruta med IoU, rutan jämnas ut med EMA och en ruta släcks först
efter ett antal missade ramar.
"""

from dataclasses import dataclass

from xray_detector.domain.detection import Detection

IOU_THRESHOLD = 0.3
ALPHA = 0.5
MIN_HITS = 2
MAX_MISSED = 3


@dataclass
class _Track:
    box: list[float]
    class_name: str
    confidence: float
    hits: int = 1
    missed: int = 0


class DetectionSmoother:
    """Jämnar ut detektioner mellan ramar med EMA och hysteres.

    alpha är vikten för den nya rutan (1.0 = ingen utjämning). En ruta
    visas först när den setts min_hits ramar, och behålls max_missed
    missade ramar innan den släcks.
    """

    def __init__(
        self,
        alpha: float = ALPHA,
        min_hits: int = MIN_HITS,
        max_missed: int = MAX_MISSED,
        iou_threshold: float = IOU_THRESHOLD,
    ) -> None:
        self.alpha = alpha
        self.min_hits = min_hits
        self.max_missed = max_missed
        self.iou_threshold = iou_threshold
        self._tracks: list[_Track] = []

    def reset(self) -> None:
        self._tracks = []

    def update(self, detections: list[Detection]) -> list[Detection]:
        used: set[int] = set()
        for track in self._tracks:
            index = self._best_match(track, detections, used)
            if index is None:
                track.missed += 1
                continue
            used.add(index)
            detection = detections[index]
            track.box = [
                self.alpha * new + (1 - self.alpha) * old
                for new, old in zip(
                    (detection.x1, detection.y1, detection.x2, detection.y2),
                    track.box,
                )
            ]
            track.confidence = detection.confidence
            track.missed = 0
            track.hits += 1
        for index, detection in enumerate(detections):
            if index not in used:
                self._tracks.append(
                    _Track(
                        box=[detection.x1, detection.y1, detection.x2, detection.y2],
                        class_name=detection.class_name,
                        confidence=detection.confidence,
                    )
                )
        self._tracks = [track for track in self._tracks if track.missed <= self.max_missed]
        return [
            Detection(
                x1=track.box[0],
                y1=track.box[1],
                x2=track.box[2],
                y2=track.box[3],
                class_name=track.class_name,
                confidence=track.confidence,
            )
            for track in self._tracks
            if track.missed == 0 and track.hits >= self.min_hits
        ]

    def _best_match(
        self,
        track: _Track,
        detections: list[Detection],
        used: set[int],
    ) -> int | None:
        best_index, best_iou = None, self.iou_threshold
        for index, detection in enumerate(detections):
            if index in used or detection.class_name != track.class_name:
                continue
            score = _iou(track.box, detection)
            if score > best_iou:
                best_index, best_iou = index, score
        return best_index


def _iou(box: list[float], detection: Detection) -> float:
    x1 = max(box[0], detection.x1)
    y1 = max(box[1], detection.y1)
    x2 = min(box[2], detection.x2)
    y2 = min(box[3], detection.y2)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area = (
        (box[2] - box[0]) * (box[3] - box[1])
        + detection.width * detection.height
        - intersection
    )
    return intersection / area if area else 0.0
