"""Sparad inspelningsmodalitet per videofönster (TASK-39).

Nycklarna ligger under detection/mode_<source_id>_*, så varje strömpanel
minns sitt eget val på samma sätt som detection/source_<id>_kind.
"""

from xray_detector.domain.capture import VideoMode

PREFIX = "detection/mode"


def _key(source_id: str, field: str) -> str:
    return f"{PREFIX}_{source_id}_{field}"


def load_video_mode(settings, source_id: str) -> VideoMode | None:
    """Panelens sparade modalitet, eller None när drivrutinen får välja."""
    width = settings.value(_key(source_id, "width"), type=int)
    height = settings.value(_key(source_id, "height"), type=int)
    if not width or not height:
        return None
    return VideoMode(
        width, height, settings.value(_key(source_id, "fourcc"), "", type=str)
    )


def save_video_mode(settings, source_id: str, mode: VideoMode) -> None:
    settings.setValue(_key(source_id, "width"), mode.width)
    settings.setValue(_key(source_id, "height"), mode.height)
    settings.setValue(_key(source_id, "fourcc"), mode.fourcc)


def clear_video_mode(settings, source_id: str) -> None:
    """Tillbaka till drivrutinens eget val."""
    for field in ("width", "height", "fourcc"):
        settings.remove(_key(source_id, field))
