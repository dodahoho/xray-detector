"""Global kraschdialog (TASK-16)."""

import logging
import sys
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from xray_detector.ui.crash_dialog import (
    excepthook_with_dialog,
    install_exception_dialog,
    restore_default_excepthook,
)


class FakeMessageBox:
    """Spelar QMessageBox sa dialogen kan testas utan att blockera."""

    Icon = SimpleNamespace(Critical="critical")
    shown = []

    def __init__(self):
        self.calls = {}
        FakeMessageBox.shown.append(self.calls)

    def setIcon(self, icon):
        self.calls["icon"] = icon

    def setWindowTitle(self, title):
        self.calls["title"] = title

    def setText(self, text):
        self.calls["text"] = text

    def setInformativeText(self, text):
        self.calls["info"] = text

    def setDetailedText(self, text):
        self.calls["detailed"] = text

    def exec(self):
        self.calls["exec"] = True


def test_unhandled_exception_shows_dialog_and_logs(qapp, monkeypatch, caplog):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox", FakeMessageBox)
    with caplog.at_level(logging.ERROR):
        try:
            raise ValueError("bang i gui-trad")
        except ValueError:
            excepthook_with_dialog(*sys.exc_info())
    assert len(FakeMessageBox.shown) == 1
    payload = FakeMessageBox.shown[-1]
    assert payload["title"] == "Ov\u00e4ntat fel"
    assert "ValueError" in payload["text"] and "bang i gui-trad" in payload["text"]
    assert "Traceback" in payload["detailed"]
    assert payload["exec"] is True
    assert "Ohanterat undantag" in caplog.text and "bang i gui-trad" in caplog.text


def test_hook_swallows_dialog_errors(qapp, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("dialog kraschade")

    class ExplodingMessageBox:
        def __getattr__(self, name):
            return boom

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox", ExplodingMessageBox)
    try:
        raise RuntimeError("felet loggas")
    except RuntimeError:
        excepthook_with_dialog(*sys.exc_info())  # far inte kasta


def test_install_and_restore(monkeypatch):
    before = sys.excepthook
    install_exception_dialog()
    assert sys.excepthook is excepthook_with_dialog
    restore_default_excepthook()
    assert sys.excepthook is sys.__excepthook__
    assert sys.excepthook is not excepthook_with_dialog or before is excepthook_with_dialog
