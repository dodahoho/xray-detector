"""GUI-tester för annoteringscanvas: rita, flytta, storleksändra, radera."""

import numpy as np
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.ui.annotation_view import AnnotationCanvas, RectItem
from xray_detector.ui.colors import class_color

# Bild 64x48 i en 160x120-canvas -> skala 2.5, origo (0,0): enkla koordinater.
CANVAS_W, CANVAS_H = 160, 120
SCALE = 2.5


def make_canvas(qapp) -> AnnotationCanvas:
    canvas = AnnotationCanvas("test")
    canvas.resize(CANVAS_W, CANVAS_H)
    canvas.set_class_name("klass")
    canvas.load_frame(
        StreamFrame(source_id="s", frame=synthetic_frame(), detections=[], source_label="kamera"),
        "klass",
    )
    canvas.show()
    qapp.processEvents()
    return canvas


def _mouse(event_type, x, y, button=Qt.MouseButton.LeftButton, old=Qt.MouseButton.NoButton):
    return QMouseEvent(event_type, QPointF(x, y), QPointF(x, y), button, old,
                       Qt.KeyboardModifier.NoModifier)


def click(canvas, x, y):
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, x, y))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, x, y))


def drag(canvas, x1, y1, x2, y2):
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, x1, y1))
    canvas.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2,
                                 Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton))
    canvas.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, x2, y2,
                                 Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, x2, y2))


def key(canvas, key_code):
    canvas.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key_code, Qt.KeyboardModifier.NoModifier))


def test_draw_creates_rect_with_class(qapp):
    canvas = make_canvas(qapp)
    drag(canvas, 50, 50, 148, 122)
    assert len(canvas.rects) == 1
    assert canvas.rects[0].class_name == "klass"
    assert canvas.selected is canvas.rects[0]


def test_move_rect(qapp):
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(20, 20, 60, 50, "klass"))
    item = canvas.rects[0]
    click(canvas, 100, 87)  # mitt i rektangeln: bild (40, 35)
    assert canvas.selected is item
    drag(canvas, 100, 87, 125, 87)
    assert item.rect.x() > 20


def test_resize_via_left_handle(qapp):
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(20, 20, 60, 50, "klass"))
    item = canvas.rects[0]
    canvas.selected = item
    left = canvas._handle_points(item.rect)["left"]
    drag(canvas, left.x() + 2, left.y(), left.x() - 25, left.y())
    assert item.rect.width() == 50
    assert item.rect.left() == 10


def test_draw_rect_too_small_is_ignored(qapp):
    canvas = make_canvas(qapp)
    drag(canvas, 50, 50, 52, 52)
    assert canvas.rects == []


def test_delete_key_removes_selected(qapp):
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(20, 20, 60, 50, "klass"))
    canvas.rects.append(RectItem(30, 40, 70, 60, "pistol"))
    first, second = canvas.rects
    canvas.selected = first
    key(canvas, Qt.Key.Key_Delete)
    assert canvas.rects == [second]
    assert canvas.selected is None


def test_backspace_key_removes_selected(qapp):
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(20, 20, 60, 50, "klass"))
    canvas.selected = canvas.rects[0]
    key(canvas, Qt.Key.Key_Backspace)
    assert canvas.rects == []


def test_result_yields_bgr_numpy(qapp):
    canvas = make_canvas(qapp)
    drag(canvas, 50, 50, 148, 122)
    result = canvas.result()
    assert result is not None
    assert result.frame.shape == (48, 64, 3)
    assert result.frame.dtype == np.uint8
    assert result.annotations[0]["bbox"][2] > 0


def test_clicking_the_class_label_emits_the_signal(qapp):
    """Klassnamnet i bilden går att klicka på (TASK-71)."""
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(20, 20, 60, 50, "klass"))
    item = canvas.rects[0]
    clicked = []
    canvas.class_label_clicked.connect(clicked.append)

    label = canvas._label_rect(item).center()
    click(canvas, label.x(), label.y())

    assert clicked == [item]
    assert canvas.selected is item


def test_clicking_the_annotation_body_does_not_emit_the_label_signal(qapp):
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(20, 20, 60, 50, "klass"))
    item = canvas.rects[0]
    clicked = []
    canvas.class_label_clicked.connect(clicked.append)

    center = canvas._handle_points(item.rect)["_center"]
    click(canvas, center.x(), center.y())

    assert clicked == []
    assert canvas.selected is item


def test_set_item_class_changes_the_class_and_marks_dirty(qapp):
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(20, 20, 60, 50, "klass"))
    item = canvas.rects[0]

    canvas.set_item_class(item, "pistol")

    assert item.class_name == "pistol"
    assert canvas.dirty


def test_annotation_is_drawn_with_the_shared_class_color(qapp):
    """Samma klass har samma färg som i dataset- och detektionsvyn (TASK-76)."""
    canvas = make_canvas(qapp)
    canvas.rects.append(RectItem(10, 10, 20, 20, "pistol"))
    canvas.selected = None

    image = canvas.grab().toImage()
    drawn = {
        image.pixelColor(x, y).name()
        for x in range(image.width())
        for y in range(image.height())
    }

    assert class_color("pistol").name() in drawn
