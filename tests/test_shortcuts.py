"""Tangentbordsgenvägar med synliga mnemonik (TASK-41)."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QPushButton

from tests.conftest import synthetic_frame
from xray_detector.domain.config import AppConfig
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def quiet_dialogs(monkeypatch):
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )


@pytest.fixture
def window(qapp, tmp_path):
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    window.show()
    window.activateWindow()
    qapp.processEvents()
    yield window
    window.detection_view.wait_for_background()
    window.close()


def alt(qapp, window, key) -> None:
    """Alt+bokstav; en knapp aktiveras först när animateClick-timern löst ut."""
    QTest.keyClick(window.windowHandle(), key, Qt.KeyboardModifier.AltModifier)
    QTest.qWait(150)
    qapp.processEvents()


def mnemonic_letter(text: str) -> str | None:
    index = text.find("&")
    return text[index + 1].lower() if index >= 0 else None


def test_tab_row_shows_mnemonics(window):
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == [
        "&Detektion",
        "&Annotation",
        "Data&set",
        "&Träning",
        "&Inställningar",
    ]


def test_alt_letter_switches_tab(qapp, window):
    alt(qapp, window, Qt.Key.Key_T)
    assert window.tabs.currentIndex() == 3

    alt(qapp, window, Qt.Key.Key_S)
    assert window.tabs.currentIndex() == 2

    alt(qapp, window, Qt.Key.Key_I)
    assert window.tabs.currentIndex() == 4


def test_disabled_tab_is_not_reached(qapp, window):
    assert not window.tabs.isTabEnabled(1)

    alt(qapp, window, Qt.Key.Key_A)

    assert window.tabs.currentIndex() == 0


def test_button_labels_show_underline_or_hint(window):
    detection = window.detection_view
    annotation = window.annotation_view
    training = window.training_view

    assert detection.capture_button.text() == "&Fånga bilder"
    assert detection.detection_button.text() == "Detekti&on av"
    assert detection.left.retry_button.text() == "Försök i&gen"
    assert detection.right.retry_button.text() == "Försök ige&n"
    assert annotation.save_button.text() == "S&para till dataset"
    assert annotation.delete_button.text() == "Ta &bort markerad"
    assert annotation.cancel_button.text() == "Avbryt (Esc)"
    assert window.dataset_view.delete_button.text() == "Ta &bort markerade"
    assert training.start_button.text() == "Sta&rta träning"
    assert training.abort_button.text() == "Avbryt (Esc)"
    assert training.export_coco_button.text() == "&Exportera COCO"
    assert training.export_yolo_button.text() == "Exportera &YOLO"


def test_mnemonics_are_unique_per_view(window):
    """Flikraden syns alltid, så knapparna får inte krocka med dess bokstäver."""
    tab_letters = [
        mnemonic_letter(window.tabs.tabText(i)) for i in range(window.tabs.count())
    ]
    assert len(tab_letters) == len(set(tab_letters))

    views = (
        window.detection_view,
        window.annotation_view,
        window.dataset_view,
        window.training_view,
        window.settings_view,
    )
    for view in views:
        letters = [
            letter
            for letter in (
                mnemonic_letter(button.text())
                for button in view.findChildren(QPushButton)
            )
            if letter
        ]
        assert len(letters) == len(set(letters)), (type(view).__name__, letters)
        assert not set(letters) & set(tab_letters), (type(view).__name__, letters)


def test_buttons_register_their_mnemonic(window):
    expected = {
        window.detection_view.capture_button: "Alt+F",
        window.detection_view.detection_button: "Alt+O",
        window.detection_view.left.retry_button: "Alt+G",
        window.detection_view.right.retry_button: "Alt+N",
        window.annotation_view.save_button: "Alt+P",
        window.annotation_view.delete_button: "Alt+B",
        window.dataset_view.delete_button: "Alt+B",
        window.training_view.start_button: "Alt+R",
        window.training_view.export_coco_button: "Alt+E",
        window.training_view.export_yolo_button: "Alt+Y",
    }

    for button, sequence in expected.items():
        assert button.shortcut().toString() == sequence, button.text()

    # Avbryt-knapparna har Esc i stället för mnemonik
    assert window.annotation_view.cancel_button.shortcut().isEmpty()
    assert window.training_view.abort_button.shortcut().isEmpty()


def test_alt_letter_toggles_detection(qapp, window):
    assert window.detection_view.detection_enabled

    alt(qapp, window, Qt.Key.Key_O)

    assert not window.detection_view.detection_enabled
    assert window.detection_view.detection_button.text() == "Detekti&on på"


def test_alt_letter_deletes_in_dataset_view(qapp, window, monkeypatch):
    window.dataset_service.add_samples(1, [AnnotatedImage(synthetic_frame(), [])])
    view = window.dataset_view
    view.refresh_versions()
    view.wait_for_refresh()
    view._on_thumb_clicked(view._thumbs[0])
    assert view.delete_button.isEnabled()
    asked = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(
            lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No
        ),
    )
    window.tabs.setCurrentIndex(2)
    qapp.processEvents()

    alt(qapp, window, Qt.Key.Key_B)

    assert asked and "Ta bort" in asked[0]


def test_alt_letter_starts_training(qapp, window):
    messages = []
    window.training_view.status_changed.connect(messages.append)
    window.tabs.setCurrentIndex(3)
    qapp.processEvents()

    alt(qapp, window, Qt.Key.Key_R)

    assert messages == ["Ingen datasetversion vald"]


def test_shortcut_on_inactive_tab_does_not_fire(qapp, window):
    messages = []
    window.detection_view.error_occurred.connect(messages.append)
    window.tabs.setCurrentIndex(2)
    qapp.processEvents()

    alt(qapp, window, Qt.Key.Key_F)

    assert messages == []

    window.tabs.setCurrentIndex(0)
    qapp.processEvents()
    alt(qapp, window, Qt.Key.Key_F)

    assert messages == ["Ingen videokälla att fånga ifrån"]


def test_escape_cancels_annotation_view(qapp, window):
    cancelled = []
    window.annotation_view.cancelled.connect(lambda: cancelled.append(True))
    window.tabs.setTabEnabled(1, True)
    window.tabs.setCurrentIndex(1)
    qapp.processEvents()

    QTest.keyClick(window.windowHandle(), Qt.Key.Key_Escape)
    qapp.processEvents()

    assert cancelled == [True]


def test_escape_does_not_fire_on_inactive_tab(qapp, window):
    cancelled = []
    window.annotation_view.cancelled.connect(lambda: cancelled.append(True))
    window.tabs.setCurrentIndex(0)
    qapp.processEvents()

    QTest.keyClick(window.windowHandle(), Qt.Key.Key_Escape)
    qapp.processEvents()

    assert cancelled == []


class _FakeScheduler:
    def __init__(self, calls: list) -> None:
        self.calls = calls

    def has_queued(self) -> bool:
        return True

    def cancel(self) -> None:
        self.calls.append("scheduler")


class _FakeTrainingService:
    def __init__(self, calls: list) -> None:
        self.calls = calls

    def scheduler(self) -> _FakeScheduler:
        return _FakeScheduler(self.calls)

    def cancel(self) -> None:
        self.calls.append("worker")


def test_escape_aborts_training(qapp, window, monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        window.training_view, "training_service", _FakeTrainingService(calls)
    )
    window.tabs.setCurrentIndex(3)
    qapp.processEvents()

    QTest.keyClick(window.windowHandle(), Qt.Key.Key_Escape)
    qapp.processEvents()

    assert calls == ["scheduler"]


def test_class_list_shortcuts(qapp, window, monkeypatch):
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    window.tabs.setTabEnabled(1, True)
    window.tabs.setCurrentIndex(1)
    qapp.processEvents()
    combo = window.annotation_view.class_combo
    combo.setEditText("ny_klass")

    QTest.keyClick(
        window.windowHandle(), Qt.Key.Key_Plus, Qt.KeyboardModifier.ControlModifier
    )
    qapp.processEvents()

    assert combo.findText("ny_klass") >= 0

    combo.setCurrentIndex(combo.findText("ny_klass"))
    QTest.keyClick(
        window.windowHandle(), Qt.Key.Key_Minus, Qt.KeyboardModifier.ControlModifier
    )
    qapp.processEvents()

    assert combo.findText("ny_klass") < 0


def test_shortcuts_do_not_collide_with_the_canvas(window):
    sequences = {shortcut.key().toString() for shortcut in window.findChildren(QShortcut)}

    assert sequences == {"F11", "Esc", "Ctrl++", "Ctrl+-"}
