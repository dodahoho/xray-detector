"""Upptäckt av UVC-videoenheter med riktiga namn (pygrabber på Windows)."""

import os
from dataclasses import dataclass

import cv2

from xray_detector.domain.capture import VideoMode


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


def _windows_device_formats(index: int) -> list[dict]:
    """Enhetens råa DirectShow-kapabiliteter (pygrabber), tom lista utan stöd."""
    if os.name != "nt":
        return []
    try:
        from pygrabber.dshow_graph import FilterGraph

        graph = FilterGraph()
        graph.add_video_input_device(index)
        return graph.get_input_device().get_formats()
    except Exception:
        return []


def list_device_modes(index: int) -> list[VideoMode]:
    """Enhetens egna upplösningar och pixelformat via DirectShow (TASK-39).

    En UVC-enhet erbjuder ett antal (upplösning, format)-par. Kortet i
    TASK-39 ger till exempel 1920x1080 i både MJPG och YUY2, där YUY2
    kapas av USB-bandbredden. Listan är avdubblad och behåller enhetens
    egen ordning. Tom lista när pygrabber saknas eller enheten inte svarar.
    """
    modes: list[VideoMode] = []
    seen: set[tuple[int, int, str]] = set()
    for entry in _windows_device_formats(index):
        key = (int(entry["width"]), int(entry["height"]), str(entry["media_type_str"]))
        if key in seen:
            continue
        seen.add(key)
        modes.append(VideoMode(width=key[0], height=key[1], fourcc=key[2]))
    return modes


def device_is_available(index: int) -> bool:
    """Snabb probing av ett enskilt index (öppnar kort, används ej vid start)."""
    capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    try:
        return capture is not None and capture.isOpened()
    finally:
        if capture is not None:
            capture.release()
