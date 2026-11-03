from __future__ import annotations

import math
import time
import threading
from typing import Optional
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal


class CameraWorker(QThread):
    """Läser kontinuerligt bildrutor från ett UVC video capture card (USB 3.0) i en egen tråd.

    Om fysisk kamera saknas och `fallback_synthetic=True` genereras en realistisk
    syntetisk röntgenvideoström så att alla lägen kan köras utan väntetid.
    """

    status_changed = Signal(int, str, bool)  # stream_id, status_msg, is_hardware

    def __init__(
        self,
        stream_id: int,
        device_index: int,
        stream_name: str,
        width: int = 1280,
        height: int = 720,
        target_fps: int = 30,
        use_dshow: bool = True,
        fallback_synthetic: bool = True,
    ) -> None:
        super().__init__()
        self.stream_id = stream_id
        self.device_index = device_index
        self.stream_name = stream_name
        self.width = width
        self.height = height
        self.target_fps = max(1, target_fps)
        self.use_dshow = use_dshow
        self.fallback_synthetic = fallback_synthetic

        self._running = False
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._current_fps: float = 0.0
        self._is_hardware: bool = False

    def get_latest_frame(self) -> tuple[Optional[np.ndarray], float]:
        """Returnerar en kopia av den senaste bildrutan samt uppmätt FPS (trådsäkert)."""
        with self._lock:
            if self._latest_frame is None:
                return None, 0.0
            return self._latest_frame.copy(), self._current_fps

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        backend = cv2.CAP_DSHOW if self.use_dshow else cv2.CAP_MSMF
        cap = cv2.VideoCapture(self.device_index, backend)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            cap.release()
            return None

        # Minimera intern buffert för lägsta möjliga latens från UVC USB 3.0
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        return cap

    def run(self) -> None:
        self._running = True
        cap = self._open_capture()

        if cap is not None:
            self._is_hardware = True
            self.status_changed.emit(
                self.stream_id,
                f"{self.stream_name}: UVC USB3.0 Ansluten (Enhet {self.device_index})",
                True,
            )
        else:
            self._is_hardware = False
            self.status_changed.emit(
                self.stream_id,
                f"{self.stream_name}: Syntetisk röntgenström (UVC-enhet {self.device_index} ej hittad)",
                False,
            )

        frame_interval = 1.0 / float(self.target_fps)
        fps_counter = 0
        fps_timer = time.perf_counter()
        tick = 0

        while self._running:
            loop_start = time.perf_counter()
            frame: Optional[np.ndarray] = None

            if cap is not None:
                ok, read_frame = cap.read()
                if ok and read_frame is not None:
                    frame = read_frame
                else:
                    # Om UVC-strömmen tappas tillfälligt
                    if self.fallback_synthetic:
                        frame = self._generate_synthetic_xray_frame(tick)
            elif self.fallback_synthetic:
                frame = self._generate_synthetic_xray_frame(tick)

            if frame is not None:
                fps_counter += 1
                now = time.perf_counter()
                elapsed_fps = now - fps_timer
                if elapsed_fps >= 0.5:
                     measured_fps = fps_counter / elapsed_fps
                     fps_counter = 0
                     fps_timer = now
                else:
                    measured_fps = self._current_fps or float(self.target_fps)

                with self._lock:
                    self._latest_frame = frame
                    self._current_fps = measured_fps

            tick += 1
            elapsed = time.perf_counter() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        if cap is not None:
            cap.release()

    def _generate_synthetic_xray_frame(self, tick: int) -> np.ndarray:
        """Skapar en realistisk falskfärgad/gråskale röntgenbild med rörliga objekt på rullband."""
        w, h = self.width, self.height
        # Ljus bakgrund som i röntgenskanner
        img = np.full((h, w, 3), (235, 238, 240), dtype=np.uint8)

        # Rullbandskanter uppe och nere
        cv2.rectangle(img, (0, 0), (w, 45), (70, 75, 80), -1)
        cv2.rectangle(img, (0, h - 45), (w, h), (70, 75, 80), -1)

        # Rörliga rullbandslinjer
        speed = 5 if self.stream_id == 1 else 6
        offset = (tick * speed) % 80
        for x in range(-offset, w, 80):
            cv2.line(img, (x, 45), (x, h - 45), (215, 220, 224), 1)

        # Väska / låda som åker över bandet
        cycle_w = w + 500
        bag_x = ((tick * speed) + (self.stream_id * 220)) % cycle_w - 250
        bag_y = int(h * 0.20)
        bag_w = 420
        bag_h = int(h * 0.60)

        # Rita väskans kontur (svagt orange/brun för organiskt material i dual-energy X-ray)
        bx1 = max(0, bag_x)
        by1 = max(50, bag_y)
        bx2 = min(w, bag_x + bag_w)
        by2 = min(h - 50, bag_y + bag_h)
        if bx2 > bx1 and by2 > by1:
            overlay = img.copy()
            cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (170, 205, 235), -1)
            cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)
            cv2.rectangle(img, (bx1, by1), (bx2, by2), (110, 145, 180), 2)

        # Objekt 1: Metallföremål (mörkblått/svart för hög densitet i röntgen)
        obj1_x = bag_x + 55
        obj1_y = bag_y + 60 + int(15 * math.sin(tick * 0.05))
        obj1_w, obj1_h = 120, 85
        if 0 <= obj1_x < w - obj1_w:
            cv2.rectangle(
                img,
                (obj1_x, obj1_y),
                (obj1_x + obj1_w, obj1_y + obj1_h),
                (95, 45, 25),
                -1,
            )
            cv2.rectangle(
                img,
                (obj1_x + 15, obj1_y + 15),
                (obj1_x + obj1_w - 15, obj1_y + obj1_h - 15),
                (60, 25, 10),
                -1,
            )

        # Objekt 2: Batteri / Elektronik (grön/blå röntgensignatur)
        obj2_x = bag_x + 225
        obj2_y = bag_y + 170
        obj2_w, obj2_h = 135, 95
        if 0 <= obj2_x < w - obj2_w:
            cv2.rectangle(
                img,
                (obj2_x, obj2_y),
                (obj2_x + obj2_w, obj2_y + obj2_h),
                (45, 115, 55),
                -1,
            )
            # Cell-linjer inuti batteriet
            for cx in range(obj2_x + 20, obj2_x + obj2_w - 10, 25):
                cv2.line(img, (cx, obj2_y + 10), (cx, obj2_y + obj2_h - 10), (25, 70, 30), 3)

        # Diskret tidsstämpel / vy-markering i hörnet
        label = f"X-RAY CAM {self.stream_id} ({'VIEW A - TOP' if self.stream_id == 1 else 'VIEW B - SIDE'})"
        cv2.putText(
            img,
            label,
            (18, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (220, 230, 240),
            2,
            cv2.LINE_AA,
        )
        return img
