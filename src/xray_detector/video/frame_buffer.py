from __future__ import annotations

import threading

import numpy as np


class LatestFrame:
    """Tradsaker behallare for den senaste bildrutan."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._frame_id = 0

    def put(self, frame: np.ndarray) -> int:
        with self._lock:
            self._frame = frame
            self._frame_id += 1
            return self._frame_id

    def get(self) -> tuple[int, np.ndarray | None]:
        with self._lock:
            return self._frame_id, self._frame

    def clear(self) -> None:
        with self._lock:
            self._frame = None
            self._frame_id = 0
