"""Verktygsvalet rita/panorera i annoteringsvyn (TASK-168).

När bilden är så inzoomad att hela bilden inte ryms i ytan får zoompanelen två
verktyg: Rita, som är valt från början och ritar en box vid klick och drag, och
Panorera, som flyttar den synliga delen av bilden i stället. Så länge hela
bilden ryms finns inget att panorera, så då döljs valet och läget är rita.
"""

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.ui.annotation_view import (
    TOOL_DRAW,
    TOOL_PAN,
    AnnotationCanvas,
    AnnotationView,
    RectItem,
)

# testerna startar MainWindow och tar därför sekunder (TASK-154)
pytestmark = pytest.mark.slow


def make_canvas(qapp, width=400, height=300) -> AnnotationCanvas:
    """Bild 64x48 i en 400x300-canvas: skalan 6.25 gör att bilden fyller ytan."""
    canvas = AnnotationCanvas("test")
    canvas.resize(width, height)
    canvas.set_class_name("klass")
    canvas.load_frame(StreamFrame("s", synthetic_frame(), [], "k"), "klass")
    canvas.show()
    qapp.processEvents()
    return canvas


def _mouse(
    event_type,
    x,
    y,
    button=Qt.MouseButton.LeftButton,
    old=Qt.MouseButton.NoButton,
    modifiers=Qt.KeyboardModifier.NoModifier,
):
    return QMouseEvent(
        event_type,
        QPointF(x, y),
        QPointF(x, y),
        button,
        old,
        modifiers,
    )


def drag(canvas, x1, y1, x2, y2, button=Qt.MouseButton.LeftButton, modifiers=None):
    modifiers = Qt.KeyboardModifier.NoModifier if modifiers is None else modifiers
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, x1, y1, button, modifiers=modifiers))
    canvas.mouseMoveEvent(
        _mouse(QEvent.Type.MouseMove, x2, y2, button, button, modifiers)
    )
    canvas.mouseReleaseEvent(
        _mouse(QEvent.Type.MouseButtonRelease, x2, y2, button, modifiers=modifiers)
    )


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


def zoomed_canvas(qapp) -> AnnotationCanvas:
    """Canvas med bilden inzoomad till 125 %, där hela bilden inte längre ryms."""
    canvas = make_canvas(qapp)
    canvas.zoom_overlay.zoom_in_button.click()
    return canvas


def test_the_tool_buttons_are_hidden_while_the_whole_image_fits(qapp):
    canvas = make_canvas(qapp)

    assert canvas.zoom_overlay.draw_button.isHidden()
    assert canvas.zoom_overlay.pan_button.isHidden()


def test_the_tool_buttons_appear_when_the_image_no_longer_fits(qapp):
    canvas = zoomed_canvas(qapp)

    assert not canvas._fits()
    assert canvas.zoom_overlay.draw_button.isVisible()
    assert canvas.zoom_overlay.pan_button.isVisible()


def test_draw_is_the_default_tool(qapp):
    canvas = zoomed_canvas(qapp)

    assert canvas._tool == TOOL_DRAW
    assert canvas.zoom_overlay.draw_button.isChecked()
    assert not canvas.zoom_overlay.pan_button.isChecked()


def test_pan_mode_moves_the_visible_part_of_the_image(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.zoom_overlay.pan_button.click()
    origin = canvas._image_origin()

    drag(canvas, 200, 150, 150, 120)

    assert canvas._tool == TOOL_PAN
    assert canvas._image_origin() == origin + QPoint(-50, -30)


def test_pan_mode_does_not_draw_a_box(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.zoom_overlay.pan_button.click()

    drag(canvas, 40, 40, 200, 160)

    assert canvas.rects == []
    assert not canvas.dirty


def test_pan_mode_does_not_move_or_select_an_annotation(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.rects.append(RectItem(10, 10, 30, 25, "klass"))
    item = canvas.rects[0]
    canvas.selected = item
    before = item.rect
    canvas.zoom_overlay.pan_button.click()

    drag(canvas, 200, 150, 150, 120)

    assert item.rect == before
    assert canvas.selected is item


def test_pan_mode_does_not_open_the_class_dialog(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.rects.append(RectItem(10, 10, 30, 25, "klass"))
    clicked = []
    canvas.class_label_clicked.connect(clicked.append)
    canvas.zoom_overlay.pan_button.click()
    label = canvas._label_rect(canvas.rects[0]).center()

    drag(canvas, label.x(), label.y(), label.x() - 20, label.y() - 20)

    assert clicked == []


def test_the_cursor_shows_the_open_hand_in_pan_mode(qapp):
    canvas = zoomed_canvas(qapp)

    canvas.zoom_overlay.pan_button.click()
    assert canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor

    canvas.zoom_overlay.draw_button.click()
    assert canvas.cursor().shape() == Qt.CursorShape.ArrowCursor


def test_draw_mode_draws_again_after_switching_back(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.zoom_overlay.pan_button.click()
    canvas.zoom_overlay.draw_button.click()

    drag(canvas, 40, 40, 200, 160)

    assert canvas._tool == TOOL_DRAW
    assert len(canvas.rects) == 1
    assert canvas.dirty


def test_the_tool_returns_to_draw_when_the_image_fits_again(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.zoom_overlay.pan_button.click()

    canvas.zoom_overlay.reset_button.click()

    assert canvas._fits()
    assert canvas._tool == TOOL_DRAW
    assert canvas.zoom_overlay.draw_button.isChecked()
    assert canvas.zoom_overlay.draw_button.isHidden()
    assert canvas.zoom_overlay.pan_button.isHidden()


def test_pan_mode_is_refused_while_the_whole_image_fits(qapp):
    canvas = make_canvas(qapp)

    canvas.set_tool(TOOL_PAN)

    assert canvas._tool == TOOL_DRAW
    assert canvas.zoom_overlay.draw_button.isChecked()


def test_a_new_frame_starts_in_draw_mode(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.zoom_overlay.pan_button.click()

    canvas.load_frame(StreamFrame("s", synthetic_frame(fill=140), [], "k"), "klass")

    assert canvas._tool == TOOL_DRAW
    assert canvas.zoom_overlay.draw_button.isChecked()
    assert canvas.zoom_overlay.pan_button.isHidden()


def test_the_middle_button_still_pans_in_draw_mode(qapp):
    canvas = make_canvas(qapp)
    origin = canvas._image_origin()

    drag(canvas, 200, 150, 180, 140, button=Qt.MouseButton.MiddleButton)

    assert canvas._tool == TOOL_DRAW
    assert canvas._image_origin() == origin + QPoint(-20, -10)


def test_ctrl_drag_pans_while_ctrl_is_held(qapp):
    """Ctrl panorerar utan att panorera-verktyget är valt (TASK-169)."""
    canvas = zoomed_canvas(qapp)
    origin = canvas._image_origin()

    drag(canvas, 200, 150, 150, 120, modifiers=Qt.KeyboardModifier.ControlModifier)

    assert canvas._image_origin() == origin + QPoint(-50, -30)


def test_ctrl_drag_does_not_draw_a_box(qapp):
    canvas = zoomed_canvas(qapp)

    drag(canvas, 40, 40, 200, 160, modifiers=Qt.KeyboardModifier.ControlModifier)

    assert canvas.rects == []
    assert not canvas.dirty


def test_ctrl_drag_keeps_the_selected_tool(qapp):
    """Ctrl är ett tillfälligt lån av panoreringen, inte ett verktygsbyte."""
    canvas = zoomed_canvas(qapp)

    drag(canvas, 200, 150, 150, 120, modifiers=Qt.KeyboardModifier.ControlModifier)

    assert canvas._tool == TOOL_DRAW
    assert canvas.zoom_overlay.draw_button.isChecked()


def test_drawing_works_again_when_ctrl_is_released(qapp):
    canvas = zoomed_canvas(qapp)
    drag(canvas, 200, 150, 150, 120, modifiers=Qt.KeyboardModifier.ControlModifier)

    drag(canvas, 40, 40, 200, 160)

    assert len(canvas.rects) == 1


def test_ctrl_drag_pans_even_when_the_pan_tool_is_selected(qapp):
    canvas = zoomed_canvas(qapp)
    canvas.zoom_overlay.pan_button.click()
    origin = canvas._image_origin()

    drag(canvas, 200, 150, 150, 120, modifiers=Qt.KeyboardModifier.ControlModifier)

    assert canvas._image_origin() == origin + QPoint(-50, -30)


def test_ctrl_wheel_still_zooms_and_does_not_pan(qapp):
    """Ctrl+hjul behåller zoomningen, så Ctrl+drag inte tar över hjulet (TASK-169)."""
    canvas = make_canvas(qapp)
    origin = canvas._image_origin()

    wheel(canvas, 120)

    assert canvas._zoom == pytest.approx(1.25)
    assert canvas._image_origin() != origin


def test_the_cursor_shows_the_open_hand_while_ctrl_is_held(qapp):
    canvas = make_canvas(qapp)

    canvas.mouseMoveEvent(
        _mouse(
            QEvent.Type.MouseMove,
            200,
            150,
            Qt.MouseButton.NoButton,
            modifiers=Qt.KeyboardModifier.ControlModifier,
        )
    )

    assert canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor


def test_the_tool_buttons_show_icons_instead_of_text(qapp):
    """Knapparna visar en penna och en hand, med texten kvar som tillgängligt namn."""
    canvas = zoomed_canvas(qapp)
    overlay = canvas.zoom_overlay

    for widget, name in ((overlay.draw_button, "Rita"), (overlay.pan_button, "Panorera")):
        assert widget.text() == ""
        assert not widget.icon().isNull()
        assert widget.accessibleName() == name
        assert widget.toolTip().startswith(name)


def test_the_panel_shrinks_when_the_tool_buttons_are_hidden(qapp):
    canvas = make_canvas(qapp)
    narrow = canvas.zoom_overlay.width()

    canvas.zoom_overlay.zoom_in_button.click()
    qapp.processEvents()

    assert canvas.zoom_overlay.width() > narrow


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


def test_each_image_in_the_annotation_view_has_its_own_tool(qapp, tmp_path):
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
    left.zoom_overlay.zoom_in_button.click()
    left.zoom_overlay.pan_button.click()

    assert left._tool == TOOL_PAN
    assert right._tool == TOOL_DRAW
    assert right.zoom_overlay.pan_button.isHidden()


def test_an_empty_canvas_keeps_no_tool_from_the_previous_pair(qapp, tmp_path):
    """Ett bildpar som bara har en bild kvar ska inte visa panorera (TASK-168)."""
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
    right = view.canvases[1]
    right.zoom_overlay.zoom_in_button.click()
    right.zoom_overlay.pan_button.click()

    view.load_captures([StreamFrame("l", np.full((48, 64, 3), 100, np.uint8), [], "k")])

    assert right._tool == TOOL_DRAW
    assert right.zoom_overlay.pan_button.isHidden()
