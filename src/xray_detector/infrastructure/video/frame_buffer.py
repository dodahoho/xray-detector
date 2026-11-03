"""Thread-safe latest-frame buffers."""

from __future__ import annotations

import threading

import numpy as np

from xray_detector.domain.detection import FramePacket


class FrameBuffer:
    def __init__(self, role: str) -> None:
        self.role = role
        self._lock = threading.Lock()
        self._sequence = 0
        self._packet: FramePacket | None = None

    def update(self, frame: np.ndarray, timestamp: float) -> FramePacket:
        with self._lock:
            self._sequence += 1
            packet = FramePacket(
                role=self.role,
                sequence=self._sequence,
                frame=frame,
                timestamp=timestamp,
            )
            self._packet = packet
            return packet

    def latest(self) -> FramePacket | None:
        with self._lock:
            return self._packet

    def snapshot(self) -> FramePacket | None:
        with self._lock:
            if self._packet is None:
                return None
            return FramePacket(
                role=self._packet.role,
                sequence=self._packet.sequence,
                frame=self._packet.frame.copy(),
                timestamp=self._packet.timestamp,
            )

    def clear(self) -> None:
        with self._lock:
            self._packet = None
