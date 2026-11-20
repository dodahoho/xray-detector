"""Tidsmässig utjämning och prediktion av detektioner mellan ramar (TASK-33, TASK-174).

Modellen ger små variationer i rutans position och storlek från ram till
ram, och en detektion nära confidence-tröskeln kan slå av och på. Utan
utjämning upplevs overlayn som ryckig. Här matchas varje detektion mot en
spårad ruta med IoU, rutan följs med ett alpha-beta-filter och en ruta
släcks först efter ett antal missade ramar.

Filtret håller både position och hastighet, så utjämningen inte kostar
någon eftersläpning: rutan extrapoleras till den ram den ska ritas på i
stället för att släpa efter med (1 - alpha) / alpha ramar som en ren EMA.
"""

from dataclasses import dataclass

from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.training.metrics import iou_matrix

IOU_THRESHOLD = 0.3
ALPHA = 0.5
# beta = alpha² / (2 - alpha) ger ett kritiskt dämpat filter
BETA = ALPHA**2 / (2 - ALPHA)
MIN_HITS = 2
MAX_MISSED = 3
# ett längre uppehåll ger ingen meningsfull hastighet, så rutan extrapoleras inte
MAX_DT = 0.2


@dataclass
class _Track:
    box: list[float]
    velocity: list[float]
    class_name: str
    confidence: float
    hits: int = 1
    missed: int = 0


class DetectionSmoother:
    """Jämnar ut detektioner mellan ramar och predikterar nästa ram.

    alpha är vikten för den nya rutan (1.0 = ingen utjämning) och beta hur
    snabbt hastigheten följer felet. En ruta visas först när den setts
    min_hits ramar, och behålls max_missed missade ramar innan den släcks.
    """

    def __init__(
        self,
        alpha: float = ALPHA,
        beta: float = BETA,
        min_hits: int = MIN_HITS,
        max_missed: int = MAX_MISSED,
        iou_threshold: float = IOU_THRESHOLD,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.min_hits = min_hits
        self.max_missed = max_missed
        self.iou_threshold = iou_threshold
        self._tracks: list[_Track] = []

    def reset(self) -> None:
        self._tracks = []

    def update(self, detections: list[Detection], dt: float) -> list[Detection]:
        """Matchar, korrigerar och returnerar rutorna en ram framåt.

        dt är tiden i sekunder sedan föregående anrop, alltså tiden till den
        ram rutorna ska ritas på. Saknas den, eller är den orimligt lång,
        extrapoleras rutan inte.
        """
        step = dt if 0 < dt <= MAX_DT else 0.0
        used: set[int] = set()
        for track in self._tracks:
            index = self._best_match(track, detections, used)
            if index is None:
                track.missed += 1
                continue
            used.add(index)
            detection = detections[index]
            target = [detection.x1, detection.y1, detection.x2, detection.y2]
            predicted = _extrapolate(track.box, track.velocity, step)
            residual = [
                new - old for new, old in zip(target, predicted, strict=True)
            ]
            track.box = [
                old + self.alpha * error
                for old, error in zip(predicted, residual, strict=True)
            ]
            if step:
                # andra träffen saknar hastighet: ta hela felet, så rutan inte
                # börjar sitt liv med att släpa efter
                gain = 1.0 if track.hits == 1 else self.beta
                track.velocity = [
                    velocity + gain / step * error
                    for velocity, error in zip(track.velocity, residual, strict=True)
                ]
            track.confidence = detection.confidence
            track.missed = 0
            track.hits += 1
        for index, detection in enumerate(detections):
            if index not in used:
                self._tracks.append(
                    _Track(
                        box=[detection.x1, detection.y1, detection.x2, detection.y2],
                        velocity=[0.0, 0.0, 0.0, 0.0],
                        class_name=detection.class_name,
                        confidence=detection.confidence,
                    )
                )
        self._tracks = [track for track in self._tracks if track.missed <= self.max_missed]
        shown: list[Detection] = []
        for track in self._tracks:
            if track.missed or track.hits < self.min_hits:
                continue
            box = _extrapolate(track.box, track.velocity, step)
            shown.append(
                Detection(
                    x1=box[0],
                    y1=box[1],
                    x2=box[2],
                    y2=box[3],
                    class_name=track.class_name,
                    confidence=track.confidence,
                )
            )
        return shown

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


def _extrapolate(box: list[float], velocity: list[float], step: float) -> list[float]:
    """Rutan step sekunder framåt, med en hastighet per kant."""
    return [
        position + speed * step
        for position, speed in zip(box, velocity, strict=True)
    ]


def _iou(box: list[float], detection: Detection) -> float:
    """IoU mellan en sparad ruta och en detektion, med metrics-sviten (TASK-140)."""
    return float(
        iou_matrix(
            [box],
            [[detection.x1, detection.y1, detection.x2, detection.y2]],
        )[0][0]
    )
