"""Förvald katalog i filväljaren för videofiler (TASK-85).

Första gången dialogen öppnas ligger den i projektets media/, där demovideorna
finns. Väljer man en fil någon annanstans kommer nästa dialog ihåg den
katalogen i stället, så samma mapp slipper letas upp varje gång.
"""

from pathlib import Path

from xray_detector.domain.config import PROJECT_ROOT

DEFAULT_DIR = PROJECT_ROOT / "media"
DIR_KEY = "detection/file_dir"


def video_file_dir(settings) -> str:
    """Katalogen filväljaren öppnas i: senast valda, annars media/.

    En sparad katalog som inte längre finns hoppas över, så dialogen aldrig
    öppnas i en borttagen mapp.
    """
    if settings is not None:
        saved = settings.value(DIR_KEY, "", type=str)
        if saved and Path(saved).is_dir():
            return saved
    return str(DEFAULT_DIR)


def remember_video_file(settings, path) -> None:
    """Sparar katalogen för vald videofil till nästa dialog."""
    if settings is None:
        return
    directory = Path(path).parent
    if directory.is_dir():
        settings.setValue(DIR_KEY, str(directory))
