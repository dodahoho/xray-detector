"""Video source abstraction and factory."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from xray_detector.config import VideoSourceSettings


@dataclass
class SourceSpec:
    role: str
    type: str = "device"
    index: int = 0
    file: str | None = None
    width: int = 1920
    height: int = 1080
    fps: int = 30
    backend: str = "auto"
    loop_file: bool = True

    @classmethod
    def from_settings(cls, role: str, settings: VideoSourceSettings) -> SourceSpec:
        return cls(
            role=role,
            type=settings.type,
            index=settings.index,
            file=settings.file,
            width=settings.width,
            height=settings.height,
            fps=settings.fps,
            backend=settings.backend,
            loop_file=settings.loop_file,
        )

    @property
    def description(self) -> str:
        if self.type == "file":
            return f"fil: {self.file}"
        if self.type == "test_pattern":
            return "testsignal"
        return f"enhet {self.index} ({self.backend})"


class VideoSource(ABC):
    """A source that returns BGR frames."""

    def __init__(self, spec: SourceSpec) -> None:
        self.spec = spec

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> np.ndarray | None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def at_end(self) -> bool: ...

    @property
    def description(self) -> str:
        return self.spec.description

    def __enter__(self) -> VideoSource:
        self.open()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class OpenCVVideoSource(VideoSource):
    def __init__(self, spec: SourceSpec) -> None:
        super().__init__(spec)
        self._capture: cv2.VideoCapture | None = None
        self._at_end = False
        self._is_file = spec.type == "file"

    @staticmethod
    def _running_windows() -> bool:
        import os

        return os.name == "nt"

    def _candidate_backends(self) -> list[int]:
        """Return an ordered list of backend flags to try for this source.

        CAP_ANY is tried first because OpenCV's auto-detection is the most
        reliable path and avoids driver-lock issues that occur when a
        specific backend fails before a subsequent attempt.
        """
        if self._is_file:
            return [cv2.CAP_ANY]
        if not self._running_windows():
            return [cv2.CAP_V4L2 if hasattr(cv2, "CAP_V4L2") else cv2.CAP_ANY]
        # CAP_ANY first (most reliable on Windows), then specific backends
        candidates = [cv2.CAP_ANY]
        preferred = (self.spec.backend or "auto").lower()
        # Preferred specific backend second
        if preferred == "msmf" and hasattr(cv2, "CAP_MSMF"):
            candidates.append(cv2.CAP_MSMF)
        elif preferred == "dshow" and hasattr(cv2, "CAP_DSHOW"):
            candidates.append(cv2.CAP_DSHOW)
        # Remaining specific backends as last resort
        for name in ("CAP_MSMF", "CAP_DSHOW"):
            flag = getattr(cv2, name, None)
            if flag is not None and flag not in candidates:
                candidates.append(flag)
        return candidates

    def open(self) -> None:
        if self._is_file:
            if not self.spec.file:
                raise ValueError("File source requires a file path")
            path = Path(self.spec.file)
            if not path.exists():
                raise FileNotFoundError(f"Video file not found: {path}")
            self._capture = cv2.VideoCapture(str(path), cv2.CAP_ANY)
        else:
            index = int(self.spec.index)
            errors: list[str] = []
            for flag in self._candidate_backends():
                cap = cv2.VideoCapture(index, flag)
                if cap and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.spec.width))
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.spec.height))
                    cap.set(cv2.CAP_PROP_FPS, int(self.spec.fps))
                    self._capture = cap
                    break
                cap.release()
                errors.append(f"0x{flag:04X}")
                # Brief pause to let the driver release the device
                time.sleep(0.3)
            if self._capture is None:
                raise RuntimeError(
                    f"Could not open video source {self.spec.role}: "
                    f"{self.spec.description} (backends tried: {', '.join(errors)})"
                )
        self._at_end = False

    def read(self) -> np.ndarray | None:
        if self._capture is None:
            raise RuntimeError("Video source is not open")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            if self._is_file and self.spec.loop_file:
                self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._capture.read()
                if not ok or frame is None:
                    self._at_end = True
                    return None
            else:
                self._at_end = True
                return None
        self._at_end = False
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def at_end(self) -> bool:
        return self._at_end


class SyntheticVideoSource(VideoSource):
    """Synthetic source for development and automated tests."""

    def __init__(self, spec: SourceSpec) -> None:
        super().__init__(spec)
        self._started = time.monotonic()
        self._frame_index = 0

    def open(self) -> None:
        self._started = time.monotonic()
        self._frame_index = 0

    def read(self) -> np.ndarray | None:
        width, height = max(64, self.spec.width), max(64, self.spec.height)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (24, 24, 28)
        color = (80, 180, 255) if self.spec.role == "cam0" else (255, 160, 80)
        t = self._frame_index / max(1, self.spec.fps)
        x = int((width - width * 0.22) * (0.5 + 0.5 * np.sin(t * 1.1)))
        y = int((height - height * 0.28) * (0.5 + 0.5 * np.cos(t * 0.8)))
        w, h = int(width * 0.22), int(height * 0.28)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
        cv2.putText(
            frame,
            f"{self.spec.role}  {t:7.2f}s",
            (30, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (230, 230, 230),
            2,
            cv2.LINE_AA,
        )
        self._frame_index += 1
        return frame

    def close(self) -> None:
        pass

    @property
    def at_end(self) -> bool:
        return False


def create_source(spec: SourceSpec) -> VideoSource:
    if spec.type == "test_pattern":
        return SyntheticVideoSource(spec)
    return OpenCVVideoSource(spec)
