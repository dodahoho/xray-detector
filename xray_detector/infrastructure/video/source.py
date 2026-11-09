from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class SourceInfo:
    label: str


class VideoSource(ABC):
    def __init__(self, info: SourceInfo) -> None:
        self.info = info
        self._capture: cv2.VideoCapture | None = None

    @abstractmethod
    def _open(self) -> cv2.VideoCapture: ...

    def open(self) -> None:
        if self._capture is None:
            self._capture = self._open()

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def read(self) -> np.ndarray | None:
        self.open()
        assert self._capture is not None
        ok, frame = self._capture.read()
        if not ok:
            return None
        return frame

    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()


class UvcSource(VideoSource):
    def __init__(self, device_index: int) -> None:
        super().__init__(SourceInfo(label=f"UVC {device_index}"))
        self.device_index = device_index

    def _open(self) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(self.device_index, cv2.CAP_MSMF)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(self.device_index)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        # Drivrutinens interna buffert haller bara senaste ramen: lag latens.
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return capture


class FileSource(VideoSource):
    def __init__(self, path: Path) -> None:
        super().__init__(SourceInfo(label=path.name))
        self.path = path
        self._last_read = 0.0
        self._frame_interval = 0.0

    def _open(self) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(str(self.path))
        fps = capture.get(cv2.CAP_PROP_FPS)
        self._frame_interval = 1.0 / fps if fps and fps > 0 else 1.0 / 30.0
        return capture

    def read(self) -> np.ndarray | None:
        import time

        elapsed = time.perf_counter() - self._last_read
        if elapsed < self._frame_interval:
            time.sleep(self._frame_interval - elapsed)
        self._last_read = time.perf_counter()
        frame = super().read()
        if frame is None:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            frame = super().read()
        return frame
