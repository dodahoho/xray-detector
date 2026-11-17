"""Datasetvyns knapp för att ta bort oanvända klasser (TASK-109)."""

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from xray_detector.application.dataset_service import DatasetService
from xray_detector.domain.dataset import AnnotatedImage
from xray_detector.ui.dataset_view import DatasetView


def _sample(class_name: str = "kniv", fill: int = 60) -> AnnotatedImage:
    return AnnotatedImage(
        np.full((30, 40, 3), fill, np.uint8),
        [{"class_name": class_name, "bbox": [2, 2, 8, 8]}],
    )


@pytest.fixture
def service(tmp_path) -> DatasetService:
    svc = DatasetService(tmp_path / "datasets")
    svc.set_classes(["kniv", "pistol", "cannabis"])
    svc.add_samples([_sample("kniv"), _sample("kniv", 120)])
    return svc


@pytest.fixture
def settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def _answer(monkeypatch, button, messages: list[str] | None = None) -> None:
    """Svarar på QMessageBox.question och samlar dialogtexterna."""

    def question(parent, title, text, *args, **kwargs):
        if messages is not None:
            messages.append(text)
        return button

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))


def test_the_view_has_a_button_for_unused_classes(qapp, config, service, settings):
    view = DatasetView(config, service, settings)
    view.wait_for_refresh()

    assert view.unused_classes_button.text().replace("&", "") == (
        "Ta bort oanvända klasser"
    )


def test_the_button_removes_the_unused_classes(
    qapp, config, service, settings, monkeypatch
):
    view = DatasetView(config, service, settings)
    view.wait_for_refresh()
    messages: list[str] = []
    _answer(monkeypatch, QMessageBox.StandardButton.Yes, messages)
    statuses: list[str] = []
    view.status_changed.connect(statuses.append)

    view.unused_classes_button.click()
    view.wait_for_refresh()

    assert service.classes() == ["kniv"]
    assert "pistol" in messages[0] and "cannabis" in messages[0]
    assert statuses == ["Tog bort 2 oanvända klasser"]
    # klassfiltret följer den rensade listan
    assert view.class_combo.findData("pistol") < 0


def test_the_button_reports_when_every_class_is_used(
    qapp, config, service, settings, monkeypatch
):
    service.set_classes(["kniv"])
    view = DatasetView(config, service, settings)
    view.wait_for_refresh()
    _answer(monkeypatch, QMessageBox.StandardButton.Yes)
    statuses: list[str] = []
    view.status_changed.connect(statuses.append)

    view.unused_classes_button.click()

    assert statuses == ["Alla klasser i datasetet används"]
    assert service.classes() == ["kniv"]


def test_a_declined_dialog_keeps_the_class_list(
    qapp, config, service, settings, monkeypatch
):
    view = DatasetView(config, service, settings)
    view.wait_for_refresh()
    _answer(monkeypatch, QMessageBox.StandardButton.No)

    view.unused_classes_button.click()

    assert service.classes() == ["kniv", "pistol", "cannabis"]
