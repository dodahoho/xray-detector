"""Upptäckt av UVC-videoenheter med riktiga namn (pygrabber på Windows)."""

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
        from pygrabber.dshow_graph import FilterGraph

        names = FilterGraph().get_input_devices()
        return dict(enumerate(names))
    except Exception:
        return {}


def list_devices(max_fallback: int = 2) -> list[DeviceInfo]:
    """Listar tilgängliga videoenheter.

    Med pygrabber på Windows returneras de faktiska enhetsnamnen. Utan
    pygrabber faller funktionen tillbaka på indexen 0..max_fallback-1
    (inga kameror öppnas, så startkostnaden är noll).
    """
    try:
        names = _windows_device_names()
    except Exception:
        names = {}
    if names:
        return [DeviceInfo(index, name) for index, name in sorted(names.items())]
    return [DeviceInfo(index, f"Video {index}") for index in range(max_fallback)]


def device_is_available(index: int) -> bool:
    """Snabb probing av ett enskilt index (öppnar kort, används ej vid start)."""
    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    try:
        return capture is not None and capture.isOpened()
    finally:
        if capture is not None:
            capture.release()
