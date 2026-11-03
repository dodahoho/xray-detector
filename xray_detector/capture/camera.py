"""Kamera-källa: öppna/stänga UVC-kameror via OpenCV.

Backend-val:
- Windows: DSHOW (default för UVC-kort)
- Linux: V4L2
- "auto": väljer baserat på OS
"""
from __future__ import annotations

import platform
import sys

import cv2
from loguru import logger

from xray_detector.config import StreamConfig


def _pick_backend(backend: str) -> int:
    """Översätt backend-sträng till OpenCV CAP_*-konstant."""
    if backend == "dshow":
        return cv2.CAP_DSHOW
    if backend == "v4l2":
        return cv2.CAP_V4L2
    # auto
    if sys.platform.startswith("win"):
        return cv2.CAP_DSHOW
    return cv2.CAP_V4L2


class CameraSource:
    """En videoström (ett capture-kort)."""

    def __init__(self, stream: StreamConfig, backend: str = "auto"):
        self.stream = stream
        self.backend = backend
        self._cap: cv2.VideoCapture | None = None

    @property
    def open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def open_camera(self) -> bool:
        """Öppna kameran. Returnerar True vid framgång."""
        self.close()
        api = _pick_backend(self.backend)
        logger.info(
            "Öppnar kamera index={} backend={} {}x{}@{}fps",
            self.stream.index, self.backend,
            self.stream.width, self.stream.height, self.stream.fps,
        )
        self._cap = cv2.VideoCapture(self.stream.index, api)
        if not self._cap.isOpened():
            # Fallback: försök utan explicit backend
            logger.warning(
                "Backend {} misslyckades för index={}, försöker default",
                self.backend, self.stream.index,
            )
            self._cap = cv2.VideoCapture(self.stream.index)
            if not self._cap.isOpened():
                logger.error("Kunde inte öppna kamera index={}", self.stream.index)
                self._cap = None
                return False
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.stream.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.stream.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.stream.fps)
        return True

    def read(self) -> tuple[bool, "cv2.Mat | None"]:
        """Läs ett frame. Returnerar (ok, frame)."""
        if not self.open:
            return False, None
        ok, frame = self._cap.read()
        return ok, frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "CameraSource":
        self.open_camera()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
