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
        self._deadline: float | None = None
        self._frame_interval = 0.0

    def _open(self) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(str(self.path))
        fps = capture.get(cv2.CAP_PROP_FPS)
        self._frame_interval = 1.0 / fps if fps and fps > 0 else 1.0 / 30.0
        self._deadline = None
        return capture

    def read(self) -> np.ndarray | None:
        self._wait_for_next_frame()
        frame = super().read()
        if frame is None:
            # loopen: borja om fran forsta ramen och nollstall takten
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._deadline = None
            frame = super().read()
        return frame

    def _wait_for_next_frame(self) -> None:
        """Vantar mot en fast deadline sa att uppspelningen inte driver.

        Tidigare räknades väntetiden från föregående läsning och klockan
        sattes till den faktiska tiden efter sleep, så sleep-överslaget
        lades till varje ram: uppspelningen gick 0,6 % för långsamt och
        fasen drev mot skärmens uppdatering. Nu flyttas deadline fram
        exakt en ram i taget.
        """
        import time

        now = time.perf_counter()
        if self._deadline is None:
            self._deadline = now
        self._deadline += self._frame_interval
        delay = self._deadline - now
        if delay > 0:
            time.sleep(delay)
        else:
            # vi ligger efter: borja om fran nu i stallet for att spara skuld
            self._deadline = time.perf_counter()
