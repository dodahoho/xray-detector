"""Detector factory."""

from __future__ import annotations

from xray_detector.config import DetectionSettings
from xray_detector.domain.detection import ModelMetadata
from xray_detector.infrastructure.detectors.base import Detector, DetectorError
from xray_detector.infrastructure.detectors.rfdetr_detector import RfDetrDetector
from xray_detector.infrastructure.detectors.ultralytics_yolo import UltralyticsYoloDetector


def create_detector(metadata: ModelMetadata, settings: DetectionSettings) -> Detector:
    family = metadata.family.lower()
    if family == "yolo":
        return UltralyticsYoloDetector(metadata, settings)
    if family == "rfdetr":
        return RfDetrDetector(metadata, settings)
    raise DetectorError(f"Unsupported model family: {metadata.family}")
