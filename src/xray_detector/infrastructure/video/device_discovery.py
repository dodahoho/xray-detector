"""Discovery of local video capture devices."""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2


@dataclass
class DeviceInfo:
    index: int
    name: str


def _windows_device_names() -> dict[int, str]:
    if os.name != "nt":
        return {}
    try:
        from pygrabber.dshow_graph import FilterGraph  # type: ignore

        names = FilterGraph().get_input_devices()
        return dict(enumerate(names))
    except Exception:
        return {}


def list_devices(max_index: int = 8, probe: bool = True) -> list[DeviceInfo]:
    """List video devices. Probing opens each index briefly."""
    names = _windows_device_names()
    if not probe and names:
        return [DeviceInfo(index=index, name=name) for index, name in sorted(names.items())]

    devices: list[DeviceInfo] = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index)
        try:
            if capture is not None and capture.isOpened():
                devices.append(DeviceInfo(index=index, name=names.get(index, f"Video {index}")))
        finally:
            if capture is not None:
                capture.release()
    if not devices and names:
        devices = [DeviceInfo(index=index, name=name) for index, name in sorted(names.items())]
    return devices
