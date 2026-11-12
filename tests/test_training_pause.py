"""Videoströmmar och detektion stängs av under träning (TASK-74)."""

import pytest
from PySide6.QtCore import QSettings

from tests.conftest import FakeDetector
from xray_detector.domain.config import AppConfig
from xray_detector.ui.detection_view import S_PAUSED, DetectionView


@pytest.fixture
def view(qapp, tmp_path, monkeypatch) -> DetectionView:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(
        config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    )
    view._detector_calls = []
    view._stopped = []
    view._sources = []
    monkeypatch.setattr(view.video_service, "set_detector", view._detector_calls.append)
    monkeypatch.setattr(
        view.video_service, "stop_all", lambda: view._stopped.append(True)
    )
    monkeypatch.setattr(
        view.video_service, "set_source", lambda *args: view._sources.append(args)
    )
    return view


def _with_sources(view) -> None:
    """Låter panelerna ha en UVC-kamera och en videofil som senaste källa."""
    view.left._active = ("uvc", 0)
    view.right._active = ("file", "video.mp4")


def test_training_start_stops_the_streams_and_the_detection(view):
    view.detector = FakeDetector()
    _with_sources(view)

    view.pause_detection()

    assert view._stopped == [True], "videofångsten och uppspelningen ska stängas av"
    assert view._detector_calls == [None], "detektionen ska kopplas bort"
    assert view.detector is None
    assert view.left.display.text() == S_PAUSED
    assert view.right.display.text() == S_PAUSED
    assert view.left.latest is None and view.right.latest is None


def test_detection_tab_restarts_the_same_sources(view, monkeypatch):
    _with_sources(view)
    view.pause_detection()
    monkeypatch.setattr(view, "_on_model_changed", lambda: None)

    view.resume_streams()

    assert [call[0] for call in view._sources] == ["left", "right"]
    assert view._sources[0][1:3] == ("uvc", 0)
    assert view._sources[1][1:3] == ("file", "video.mp4")


def test_resume_streams_does_nothing_when_not_paused(view):
    _with_sources(view)

    view.resume_streams()

    assert view._sources == []


def test_detection_tab_keeps_the_detection_off(view, monkeypatch):
    view.detector = FakeDetector()
    view.detection_button.setChecked(False)
    view.pause_detection()
    monkeypatch.setattr(
        view, "_on_model_changed", lambda: pytest.fail("modellen ska inte laddas om")
    )
    view._detector_calls.clear()

    view.resume_streams()

    assert view._detector_calls == []


def test_training_finish_restarts_the_streams(view, monkeypatch):
    _with_sources(view)
    view.pause_detection()
    monkeypatch.setattr(view, "_on_model_changed", lambda: None)

    view.resume_detection()

    assert [call[0] for call in view._sources] == ["left", "right"]


def test_pause_stops_a_running_stream_worker(qapp, tmp_path, video_file):
    """Den riktiga kameratråden stängs av, inte bara detektorn (TASK-74)."""
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(
        config, QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    )
    view._on_source_requested("left", "file", video_file)
    worker = view.video_service.camera_service.worker("left")
    assert worker is not None and worker.isRunning()

    view.pause_detection()

    assert view.video_service.camera_service.worker("left") is None
    assert not worker.isRunning()


def test_training_start_and_the_detection_tab_drive_the_streams(
    qapp, config, monkeypatch
):
    """Träningsstarten stänger av strömmarna och fliken Detektion tänder dem."""
    from xray_detector.ui.main_window import MainWindow

    window = MainWindow(config)
    view = window.detection_view
    stopped: list = []
    sources: list = []
    monkeypatch.setattr(view.video_service, "stop_all", lambda: stopped.append(True))
    monkeypatch.setattr(
        view.video_service, "set_source", lambda *args: sources.append(args)
    )
    monkeypatch.setattr(view, "_on_model_changed", lambda: None)
    view.left._active = ("uvc", 0)

    window._on_training_started()

    assert stopped == [True]
    assert view.left.display.text() == S_PAUSED

    window.tabs.setCurrentIndex(2)
    assert sources == [], "bara fliken Detektion ska tända strömmarna"

    window.tabs.setCurrentIndex(0)

    assert [call[0] for call in sources] == ["left"]
    view.wait_for_background()
    window.dataset_view.wait_for_refresh()
    window.close()
