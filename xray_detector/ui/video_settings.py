"""Sparad inspelningsmodalitet för UVC-källor (TASK-39).

Delas av inställningsvyn som skriver valet och detektionsvyn som läser det
när en UVC-källa öppnas, så nycklarna bara finns på ett ställe.
"""

from xray_detector.domain.capture import VideoMode

WIDTH_KEY = "video/width"
HEIGHT_KEY = "video/height"
FOURCC_KEY = "video/fourcc"


def load_video_mode(settings) -> VideoMode | None:
    """Sparad modalitet, eller None när inget val gjorts (drivrutinen väljer)."""
    width = settings.value(WIDTH_KEY, type=int)
    height = settings.value(HEIGHT_KEY, type=int)
    if not width or not height:
        return None
    return VideoMode(width, height, settings.value(FOURCC_KEY, "", type=str))


def save_video_mode(settings, mode: VideoMode) -> None:
    settings.setValue(WIDTH_KEY, mode.width)
    settings.setValue(HEIGHT_KEY, mode.height)
    settings.setValue(FOURCC_KEY, mode.fourcc)


def clear_video_mode(settings) -> None:
    """Tillbaka till drivrutinens eget val."""
    for key in (WIDTH_KEY, HEIGHT_KEY, FOURCC_KEY):
        settings.remove(key)
