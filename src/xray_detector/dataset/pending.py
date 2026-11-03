from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from xray_detector.models import Detection
from xray_detector.util.files import atomic_write_json, read_json

CAMERA_LEFT = "left"
CAMERA_RIGHT = "right"


@dataclass
class PendingImage:
    camera: str
    file_name: str
    width: int
    height: int
    detections: list[Detection]

    def to_dict(self) -> dict[str, Any]:
        return {
            "camera": self.camera,
            "file_name": self.file_name,
            "width": self.width,
            "height": self.height,
            "detections": [detection.to_dict() for detection in self.detections],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingImage":
        return cls(
            camera=str(data["camera"]),
            file_name=str(data["file_name"]),
            width=int(data["width"]),
            height=int(data["height"]),
            detections=[Detection.from_dict(item) for item in data.get("detections", [])],
        )


@dataclass
class PendingCapture:
    group_id: str
    directory: Path
    timestamp: str
    images: dict[str, PendingImage]

    def image_path(self, camera: str) -> Path:
        return self.directory / self.images[camera].file_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "timestamp": self.timestamp,
            "images": {
                camera: image.to_dict() for camera, image in sorted(self.images.items())
            },
        }

    @classmethod
    def from_file(cls, path: Path) -> "PendingCapture":
        data = read_json(path)
        directory = path.parent
        images = {
            str(camera): PendingImage.from_dict(item)
            for camera, item in data.get("images", {}).items()
        }
        capture = cls(
            group_id=str(data["group_id"]),
            directory=directory,
            timestamp=str(data["timestamp"]),
            images=images,
        )
        for image in capture.images.values():
            if not (directory / image.file_name).exists():
                raise FileNotFoundError(
                    f"Bilden {image.file_name} saknas i {directory}"
                )
        return capture


def create_pending_capture(
    pending_root: Path,
    frames: dict[str, np.ndarray],
    detections: dict[str, list[Detection]] | None = None,
    group_id: str | None = None,
) -> PendingCapture:
    if not frames:
        raise ValueError("Minst en bildruta kravs")
    detections = detections or {}
    timestamp = datetime.now(timezone.utc)
    group_id = group_id or timestamp.strftime("%Y%m%d_%H%M%S_%f")
    directory = pending_root / group_id
    directory.mkdir(parents=True, exist_ok=False)

    images: dict[str, PendingImage] = {}
    try:
        for camera, frame in frames.items():
            if frame is None or frame.size == 0:
                raise ValueError(f"Tom bildruta fran {camera}")
            height, width = frame.shape[:2]
            file_name = f"{camera}.png"
            target = directory / file_name
            if not cv2.imwrite(str(target), frame):
                raise OSError(f"Kunde inte spara bildrutan {target}")
            images[camera] = PendingImage(
                camera=camera,
                file_name=file_name,
                width=width,
                height=height,
                detections=detections.get(camera, []),
            )
        capture = PendingCapture(
            group_id=group_id,
            directory=directory,
            timestamp=timestamp.isoformat(),
            images=images,
        )
        atomic_write_json(directory / "capture.json", capture.to_dict())
        return capture
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def load_pending_capture(directory: Path) -> PendingCapture:
    return PendingCapture.from_file(directory / "capture.json")


def delete_pending_capture(capture: PendingCapture) -> None:
    shutil.rmtree(capture.directory, ignore_errors=True)


def list_pending_captures(pending_root: Path) -> list[Path]:
    if not pending_root.exists():
        return []
    return sorted(
        (
            path
            for path in pending_root.iterdir()
            if path.is_dir() and (path / "capture.json").exists()
        ),
        reverse=True,
    )
