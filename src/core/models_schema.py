from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid
import numpy as np


@dataclass
class BoundingBox:
    """Representerar en detekterad eller annoterad rektangel i bildkoordinater (pixlar)."""
    x1: float
    y1: float
    x2: float
    y2: float
    class_name: str
    confidence: float = 1.0
    is_manual: bool = False
    box_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    def normalized(self) -> "BoundingBox":
        """Säkerställer att x1 <= x2 och y1 <= y2."""
        nx1, nx2 = min(self.x1, self.x2), max(self.x1, self.x2)
        ny1, ny2 = min(self.y1, self.y2), max(self.y1, self.y2)
        return BoundingBox(
            x1=nx1,
            y1=ny1,
            x2=nx2,
            y2=ny2,
            class_name=self.class_name,
            confidence=self.confidence,
            is_manual=self.is_manual,
            box_id=self.box_id,
        )

    def clamp(self, img_width: int, img_height: int) -> "BoundingBox":
        """Begränsar koordinaterna till bildens dimensioner."""
        b = self.normalized()
        return BoundingBox(
            x1=max(0.0, min(float(img_width), b.x1)),
            y1=max(0.0, min(float(img_height), b.y1)),
            x2=max(0.0, min(float(img_width), b.x2)),
            y2=max(0.0, min(float(img_height), b.y2)),
            class_name=b.class_name,
            confidence=b.confidence,
            is_manual=b.is_manual,
            box_id=b.box_id,
        )

    def to_coco_bbox(self) -> List[float]:
        """Returnerar [x, y, width, height] i COCO-format."""
        b = self.normalized()
        return [round(b.x1, 2), round(b.y1, 2), round(b.width, 2), round(b.height, 2)]

    def to_yolo_bbox(self, img_width: int, img_height: int) -> List[float]:
        """Returnerar [x_center, y_center, width, height] normaliserat (0.0 - 1.0) för YOLO."""
        if img_width <= 0 or img_height <= 0:
            return [0.0, 0.0, 0.0, 0.0]
        b = self.clamp(img_width, img_height)
        x_center = ((b.x1 + b.x2) / 2.0) / img_width
        y_center = ((b.y1 + b.y2) / 2.0) / img_height
        w = b.width / img_width
        h = b.height / img_height
        return [
            round(max(0.0, min(1.0, x_center)), 6),
            round(max(0.0, min(1.0, y_center)), 6),
            round(max(0.0, min(1.0, w)), 6),
            round(max(0.0, min(1.0, h)), 6),
        ]

    def copy(self) -> "BoundingBox":
        return BoundingBox(
            x1=self.x1,
            y1=self.y1,
            x2=self.x2,
            y2=self.y2,
            class_name=self.class_name,
            confidence=self.confidence,
            is_manual=self.is_manual,
            box_id=self.box_id,
        )


@dataclass
class StreamFrameResult:
    """Resultat för en enskild videoström (råbild + detektioner)."""
    stream_id: int
    stream_name: str
    frame_bgr: np.ndarray
    detections: List[BoundingBox] = field(default_factory=list)
    fps: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CapturedFramePair:
    """Två frysta bildrutor och deras aktuella detektioner vid tryck på Fånga-knappen."""
    stream_1_frame: np.ndarray
    stream_1_boxes: List[BoundingBox]
    stream_2_frame: np.ndarray
    stream_2_boxes: List[BoundingBox]
    captured_at: datetime = field(default_factory=datetime.now)


@dataclass
class DatasetVersionInfo:
    """Metadata för ett exporterat/låst dataset."""
    version: int
    created_at: str
    export_format: str  # "COCO", "YOLO", eller "COCO+YOLO"
    num_images: int
    num_objects: int
    classes: List[str]
    path: str

    @property
    def display_label(self) -> str:
        return (
            f"v{self.version} ({self.created_at}) – "
            f"{self.num_images} bilder, {self.num_objects} objekt [{self.export_format}]"
        )


@dataclass
class TrainingConfig:
    """Parametrar för en träningskörning."""
    base_model_name: str
    model_family: str  # "YOLO26", "YOLO", "RF-DETR", "SIMULATED"
    base_weights: str
    dataset_version: int
    dataset_path: str
    epochs: int = 30
    batch_size: int = 8
    image_size: int = 640
    learning_rate: float = 0.001
    val_split: float = 0.2
    device: str = "auto"
    pause_detection_during_training: bool = True
    schedule_mode: str = "immediate"  # "immediate", "night", "inactivity"


@dataclass
class TrainedModelInfo:
    """Metadata för en färdigtränad modell."""
    version: int  # Samma versionssiffra som datasetet som användes!
    model_family: str
    base_model_name: str
    dataset_version: int
    trained_at: str
    weights_path: str
    epochs: int
    metrics: dict = field(default_factory=dict)

    @property
    def display_label(self) -> str:
        return f"v{self.version} - {self.model_family} (Dataset v{self.dataset_version}, {self.trained_at})"
