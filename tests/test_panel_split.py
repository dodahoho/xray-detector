"""Maximera en bildkälla och justera ramen mellan dem (TASK-164).

Både detektions- och annoteringsvyn visar två bildkällor bredvid varandra.
Varje panel har en knapp som maximerar den och fäller ihop den andra, och ramen
i mitten går att dra. Den som maximerar får tillbaka båda bilderna med samma
storlekar som före maximeringen.
"""

import numpy as np
import pytest
from PySide6.QtCore import QSettings

from xray_detector.domain.capture import StreamFrame
from xray_detector.domain.config import AppConfig
from xray_detector.infrastructure.dataset_store.store import DatasetStore
from xray_detector.ui.annotation_view import AnnotationView
from xray_detector.ui.detection_view import DetectionView
from xray_detector.ui.panel_split import HANDLE_WIDTH, MAXIMIZE_TOOLTIP, RESTORE_TOOLTIP

# testerna startar annoteringsvyn och tar därför sekunder (TASK-154)
pytestmark = pytest.mark.slow


def _frames() -> list[StreamFrame]:
    return [
        StreamFrame("l", np.full((48, 64, 3), 100, np.uint8), [], "k"),
        StreamFrame("r", np.full((48, 64, 3), 160, np.uint8), [], "k"),
    ]


def _settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def annotation_view(qapp, tmp_path) -> AnnotationView:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = AnnotationView(config, DatasetStore(config.dataset_dir), _settings(tmp_path))
    view.load_captures(_frames())
    view.resize(900, 500)
    view.show()
    qapp.processEvents()
    return view


@pytest.fixture
def detection_view(qapp, tmp_path) -> DetectionView:
    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    view = DetectionView(config, _settings(tmp_path))
    view.resize(1200, 700)
    view.show()
    qapp.processEvents()
    yield view
    view.wait_for_background()


def test_each_image_in_the_annotation_view_has_a_maximize_button(annotation_view):
    left, right = annotation_view.canvases

    for canvas in (left, right):
        button = canvas.zoom_overlay.maximize_button
        assert button.isVisible()
        assert button.isCheckable()
        assert not button.isChecked()
        assert button.toolTip() == MAXIMIZE_TOOLTIP


def test_maximizing_an_image_hides_the_other(annotation_view, qapp):
    left, right = annotation_view.canvases

    left.zoom_overlay.maximize_button.click()
    qapp.processEvents()

    assert left.isVisible()
    assert not right.isVisible()
    assert annotation_view.panels.maximized() == 0
    # den maximerade bilden får hela ytan, inte bara den andras halva
    assert left.width() == annotation_view.panels.width()


def test_the_maximized_image_shows_both_again(annotation_view, qapp):
    left, right = annotation_view.canvases
    left.zoom_overlay.maximize_button.click()
    qapp.processEvents()

    left.zoom_overlay.maximize_button.click()
    qapp.processEvents()

    assert left.isVisible()
    assert right.isVisible()
    assert annotation_view.panels.maximized() is None
    assert left.zoom_overlay.maximize_button.toolTip() == MAXIMIZE_TOOLTIP


def test_the_buttons_show_which_image_is_maximized(annotation_view, qapp):
    left, right = annotation_view.canvases

    right.zoom_overlay.maximize_button.click()
    qapp.processEvents()

    assert right.zoom_overlay.maximize_button.isChecked()
    assert not left.zoom_overlay.maximize_button.isChecked()
    assert right.zoom_overlay.maximize_button.toolTip() == RESTORE_TOOLTIP


def test_restoring_keeps_the_sizes_from_before_the_maximizing(annotation_view, qapp):
    """En storlek man dragit fram ska inte tappas på vägen."""
    annotation_view.panels.setSizes([600, 300])
    qapp.processEvents()
    before = annotation_view.panels.sizes()

    annotation_view.canvases[0].zoom_overlay.maximize_button.click()
    qapp.processEvents()
    annotation_view.canvases[0].zoom_overlay.maximize_button.click()
    qapp.processEvents()

    assert annotation_view.panels.sizes() == before


def test_a_new_pair_starts_with_both_images_visible(annotation_view, qapp):
    annotation_view.canvases[0].zoom_overlay.maximize_button.click()
    qapp.processEvents()

    annotation_view.load_captures(_frames())
    qapp.processEvents()

    assert annotation_view.panels.maximized() is None
    assert all(canvas.isVisible() for canvas in annotation_view.canvases)


def test_the_divider_between_the_images_can_be_dragged(annotation_view, qapp):
    split = annotation_view.panels
    before = split.sizes()

    split.moveSplitter(300, 1)
    qapp.processEvents()

    after = split.sizes()
    assert split.handleWidth() == HANDLE_WIDTH
    assert split.handle(1).isVisible()
    assert after != before
    assert after[0] < after[1]


def test_the_divider_cannot_collapse_an_image(annotation_view, qapp):
    """Ramen går bara att dra så långt att båda bilderna fortfarande syns."""
    split = annotation_view.panels

    split.moveSplitter(0, 1)
    qapp.processEvents()

    assert all(canvas.isVisible() for canvas in annotation_view.canvases)
    assert split.sizes()[0] > 0


def test_each_stream_in_the_detection_view_has_a_maximize_button(detection_view):
    for panel in (detection_view.left, detection_view.right):
        button = panel.maximize_button
        assert button.isVisible()
        assert button.isCheckable()
        assert not button.isChecked()
        assert button.toolTip() == MAXIMIZE_TOOLTIP


def test_maximizing_a_stream_hides_the_other(detection_view, qapp):
    detection_view.left.maximize_button.click()
    qapp.processEvents()

    assert detection_view.left.isVisible()
    assert not detection_view.right.isVisible()
    assert detection_view.panels.maximized() == 0
    assert detection_view.left.width() == detection_view.panels.width()

    detection_view.left.maximize_button.click()
    qapp.processEvents()

    assert detection_view.left.isVisible()
    assert detection_view.right.isVisible()
    assert detection_view.panels.maximized() is None
