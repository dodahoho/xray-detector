"""Svenska standardknappar i Qt:s egna dialoger (TASK-83)."""

import pytest
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

from xray_detector.ui.translations import install_swedish_translations


@pytest.fixture
def swedish(qapp):
    """Installerar översättningen och tar bort den efter testet."""
    translator = install_swedish_translations(qapp)
    assert translator is not None, "qtbase_sv.qm saknas i PySide6"
    yield translator
    qapp.removeTranslator(translator)


def _text(box, flag) -> str:
    return box.button(flag).text()


def test_dialog_button_box_is_swedish(qapp, swedish):
    box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )

    assert _text(box, QDialogButtonBox.StandardButton.Ok) == "Ok"
    assert _text(box, QDialogButtonBox.StandardButton.Cancel) == "Avbryt"


def test_message_box_yes_and_no_are_swedish(qapp, swedish):
    box = QMessageBox()
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    assert _text(box, QMessageBox.StandardButton.Yes) == "&Ja"
    assert _text(box, QMessageBox.StandardButton.No) == "&Nej"


def test_message_box_save_and_discard_are_swedish(qapp, swedish):
    """Frågan om osparade annoteringar har Spara/Förkasta/Avbryt."""
    box = QMessageBox()
    box.setStandardButtons(
        QMessageBox.StandardButton.Save
        | QMessageBox.StandardButton.Discard
        | QMessageBox.StandardButton.Cancel
    )

    assert _text(box, QMessageBox.StandardButton.Save) == "Spara"
    assert _text(box, QMessageBox.StandardButton.Discard) == "Förkasta"
    assert _text(box, QMessageBox.StandardButton.Cancel) == "Avbryt"


def test_missing_translation_file_leaves_qt_texts_alone(qapp, monkeypatch):
    """Saknas qtbase_sv.qm startar appen som förut."""
    from PySide6.QtCore import QTranslator

    monkeypatch.setattr(QTranslator, "load", lambda *args, **kwargs: False)

    assert install_swedish_translations(qapp) is None
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    assert _text(box, QDialogButtonBox.StandardButton.Cancel) == "Cancel"
