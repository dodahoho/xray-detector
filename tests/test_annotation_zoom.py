"""Zoomkontroller i annoteringsvyn (TASK-163).

Varje bild har en egen panel i övre vänstra hörnet med zoom ut, aktuell nivå,
zoom in och en knapp som återgår till 100 %. Panelen ligger ovanpå bilden, så
den syns där zoomningen görs, och etiketten följer både knapparna och Ctrl+hjul.
"""

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.ui.annotation_view import (
    ZOOM_MAX,
    ZOOM_MIN,
    ZOOM_OVERLAY_MARGIN,
    AnnotationCanvas,
    AnnotationView,
)

# testerna startar MainWindow och tar därför sekunder (TASK-154)
pytestmark = pytest.mark.slow


def make_canvas(qapp, width=400, height=300) -> AnnotationCanvas:
    canvas = AnnotationCanvas("test")
    canvas.resize(width, height)
    canvas.set_class_name("klass")
    canvas.load_frame(StreamFrame("s", synthetic_frame(), [], "k"), "klass")
    canvas.show()
    qapp.processEvents()
    return canvas


def wheel(canvas, delta: int, modifiers=Qt.KeyboardModifier.ControlModifier) -> None:
    event = QWheelEvent(
        QPointF(80, 60),
        QPointF(80, 60),
        QPoint(0, 0),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        modifiers,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    canvas.wheelEvent(event)


def test_the_zoom_panel_sits_in_the_top_left_corner(qapp):
    canvas = make_canvas(qapp)
    overlay = canvas.zoom_overlay

    assert overlay.isVisible()
    assert overlay.parentWidget() is canvas
    assert (overlay.x(), overlay.y()) == (ZOOM_OVERLAY_MARGIN, ZOOM_OVERLAY_MARGIN)
    assert overlay.zoom_label.text() == "100 %"


def test_the_panel_stays_in_the_corner_when_the_canvas_is_resized(qapp):
    canvas = make_canvas(qapp)

    canvas.resize(640, 480)
    qapp.processEvents()

    assert (canvas.zoom_overlay.x(), canvas.zoom_overlay.y()) == (
        ZOOM_OVERLAY_MARGIN,
        ZOOM_OVERLAY_MARGIN,
    )


def test_the_panel_is_hidden_until_an_image_is_loaded(qapp):
    canvas = AnnotationCanvas("test")

    assert canvas.zoom_overlay.isHidden()

    canvas.load_frame(StreamFrame("s", synthetic_frame(), [], "k"), "klass")

    assert not canvas.zoom_overlay.isHidden()


def test_the_buttons_zoom_in_and_out_and_update_the_label(qapp):
    canvas = make_canvas(qapp)
    overlay = canvas.zoom_overlay

    overlay.zoom_in_button.click()
    assert canvas._zoom == pytest.approx(1.25)
    assert overlay.zoom_label.text() == "125 %"

    overlay.zoom_out_button.click()
    assert canvas._zoom == pytest.approx(1.0)
    assert overlay.zoom_label.text() == "100 %"


def test_the_buttons_zoom_around_the_image_center(qapp):
    """Knapparna zoomar kring mitten, så bilden växer åt alla håll."""
    canvas = make_canvas(qapp)
    center = canvas.rect().center()
    before = canvas._to_image(center - canvas._image_origin())

    canvas.zoom_overlay.zoom_in_button.click()

    after = canvas._to_image(center - canvas._image_origin())
    assert abs(before.x() - after.x()) <= 1
    assert abs(before.y() - after.y()) <= 1


def test_the_reset_button_returns_to_100_percent_and_centers_the_image(qapp):
    canvas = make_canvas(qapp)
    canvas.zoom_overlay.zoom_in_button.click()
    canvas.zoom_overlay.zoom_in_button.click()
    canvas._pan = QPoint(40, 25)

    canvas.zoom_overlay.reset_button.click()

    assert canvas._zoom == 1.0
    assert canvas._pan == QPoint(0, 0)
    assert canvas._image_origin() == canvas._base_origin()
    assert canvas.zoom_overlay.zoom_label.text() == "100 %"


def test_the_label_follows_ctrl_wheel(qapp):
    canvas = make_canvas(qapp)

    wheel(canvas, 120)
    assert canvas._zoom == pytest.approx(1.25)
    assert canvas.zoom_overlay.zoom_label.text() == "125 %"

    wheel(canvas, -120)
    assert canvas._zoom == pytest.approx(1.0)
    assert canvas.zoom_overlay.zoom_label.text() == "100 %"


def test_the_buttons_respect_the_zoom_limits(qapp):
    canvas = make_canvas(qapp)
    overlay = canvas.zoom_overlay

    for _ in range(20):
        overlay.zoom_in_button.click()
    assert canvas._zoom == ZOOM_MAX
    assert overlay.zoom_label.text() == "500 %"

    for _ in range(30):
        overlay.zoom_out_button.click()
    assert canvas._zoom == ZOOM_MIN
    assert overlay.zoom_label.text() == "20 %"


def test_a_new_frame_starts_at_100_percent(qapp):
    canvas = make_canvas(qapp)
    canvas.zoom_overlay.zoom_in_button.click()

    canvas.load_frame(StreamFrame("s", synthetic_frame(fill=140), [], "k"), "klass")

    assert canvas._zoom == 1.0
    assert canvas.zoom_overlay.zoom_label.text() == "100 %"


def _make_view(qapp, tmp_path):
    from PySide6.QtCore import QSettings

    from xray_detector.domain.config import AppConfig
    from xray_detector.infrastructure.dataset_store.store import DatasetStore

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    service = DatasetStore(config.dataset_dir)
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    return AnnotationView(config, service, settings)


def test_each_image_in_the_annotation_view_has_its_own_zoom_panel(qapp, tmp_path):
    view = _make_view(qapp, tmp_path)
    view.load_captures(
        [
            StreamFrame("l", np.full((48, 64, 3), 100, np.uint8), [], "k"),
            StreamFrame("r", np.full((48, 64, 3), 160, np.uint8), [], "k"),
        ]
    )
    view.resize(900, 500)
    view.show()
    qapp.processEvents()

    left, right = view.canvases
    assert left.zoom_overlay.isVisible()
    assert right.zoom_overlay.isVisible()
    assert left.zoom_overlay is not right.zoom_overlay

    left.zoom_overlay.zoom_in_button.click()
    assert left._zoom == pytest.approx(1.25)
    assert right._zoom == 1.0
