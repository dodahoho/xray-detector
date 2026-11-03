from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
from PySide6.QtCore import QObject, Signal

from src.video.camera_worker import CameraWorker


class StreamManager(QObject):
    """Hanterar de två separata UVC-videoströmmarna (Ström 1 & Ström 2)."""

    camera_status_changed = Signal(int, str, bool)

    def __init__(self, cameras_config: Dict[str, Any], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        s1_cfg = cameras_config.get("stream_1", {})
        s2_cfg = cameras_config.get("stream_2", {})

        self.worker_1 = CameraWorker(
            stream_id=1,
            device_index=int(s1_cfg.get("device_index", 0)),
            stream_name=str(s1_cfg.get("name", "Röntgenström 1")),
            width=int(s1_cfg.get("width", 1280)),
            height=int(s1_cfg.get("height", 720)),
            target_fps=int(s1_cfg.get("fps", 30)),
            use_dshow=bool(s1_cfg.get("use_dshow", True)),
            fallback_synthetic=bool(s1_cfg.get("fallback_synthetic", True)),
        )
        self.worker_2 = CameraWorker(
            stream_id=2,
            device_index=int(s2_cfg.get("device_index", 1)),
            stream_name=str(s2_cfg.get("name", "Röntgenström 2")),
            width=int(s2_cfg.get("width", 1280)),
            height=int(s2_cfg.get("height", 720)),
            target_fps=int(s2_cfg.get("fps", 30)),
            use_dshow=bool(s2_cfg.get("use_dshow", True)),
            fallback_synthetic=bool(s2_cfg.get("fallback_synthetic", True)),
        )

        self.worker_1.status_changed.connect(self.camera_status_changed.emit)
        self.worker_2.status_changed.connect(self.camera_status_changed.emit)

    def start_streams(self) -> None:
        if not self.worker_1.isRunning():
            self.worker_1.start()
        if not self.worker_2.isRunning():
            self.worker_2.start()

    def stop_streams(self) -> None:
        self.worker_1.stop()
        self.worker_2.stop()

    def get_latest_frames(self) -> tuple[tuple[Optional[np.ndarray], float], tuple[Optional[np.ndarray], float]]:
        """Hämtar senaste (bildruta, fps) från både ström 1 och ström 2."""
        return self.worker_1.get_latest_frame(), self.worker_2.get_latest_frame()
