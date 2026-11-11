"""Fönsterikonen: filen Windows ritar ur och processens identitet i aktivitetsfältet."""

import struct
import sys

import pytest

from xray_detector.app import APP_USER_MODEL_ID, ICON_PATH, _set_app_user_model_id

# Storlekarna aktivitetsfältet och Alt-Tab hämtar; saknas de ritar Windows
# en nedskalad 256x256-bild i stället och ikonen blir suddig.
TASKBAR_SIZES = {16, 32, 256}


def _ico_sizes(path) -> set[int]:
    data = path.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert reserved == 0 and kind == 1, "filen är ingen ICO"
    sizes = set()
    for index in range(count):
        width, _height = struct.unpack("<BB", data[6 + index * 16:8 + index * 16])
        sizes.add(width or 256)
    return sizes


def test_icon_file_has_the_sizes_windows_asks_for():
    assert ICON_PATH.is_file()
    assert TASKBAR_SIZES <= _ico_sizes(ICON_PATH)


def test_qicon_loads_the_icon_file(qapp):
    from PySide6.QtGui import QIcon

    icon = QIcon(str(ICON_PATH))
    assert not icon.isNull()
    assert TASKBAR_SIZES <= {size.width() for size in icon.availableSizes()}


@pytest.mark.skipif(sys.platform != "win32", reason="AppUserModelID finns bara på Windows")
def test_app_user_model_id_is_set_on_the_process():
    import ctypes
    from ctypes import wintypes

    _set_app_user_model_id()

    shell32 = ctypes.windll.shell32
    shell32.GetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.POINTER(wintypes.LPWSTR)]
    shell32.GetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
    value = wintypes.LPWSTR()
    assert shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(value)) == 0
    assert value.value == APP_USER_MODEL_ID


@pytest.mark.skipif(sys.platform != "win32", reason="WM_GETICON finns bara på Windows")
def test_window_gets_the_icon_the_taskbar_draws(qapp):
    """Aktivitetsfältet ritar fönstrets ICON_BIG, inte applikationens QIcon."""
    import ctypes
    from ctypes import wintypes

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QMainWindow

    qapp.setWindowIcon(QIcon(str(ICON_PATH)))
    window = QMainWindow()
    window.show()
    qapp.processEvents()

    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = ctypes.c_void_p
    try:
        assert user32.SendMessageW(int(window.winId()), 0x007F, 1, 0)  # WM_GETICON, ICON_BIG
    finally:
        window.close()
