"""Annotation value objects."""

from __future__ import annotations

from dataclasses import dataclass

from xray_detector.domain.detection import BBox, Detection


@dataclass
class AnnotationBox:
    """An editable annotation in image pixel coordinates."""

    bbox: BBox
    class_name: str
    score: float | None = None

    @classmethod
    def from_detection(cls, detection: Detection) -> AnnotationBox:
        return cls(
            bbox=detection.bbox,
            class_name=detection.class_name,
            score=detection.score,
        )


@dataclass
class PairAnnotations:
    """Annotations for a captured image pair."""

    cam0: list[AnnotationBox]
    cam1: list[AnnotationBox]
