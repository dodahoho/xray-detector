"""Annoterings-UX (TASK-14): zoom/pan, osparade ändringar, negativa exempel."""

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QCloseEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from tests.conftest import synthetic_frame
from xray_detector.domain.capture import StreamFrame
from xray_detector.ui.annotation_view import AnnotationCanvas, AnnotationView, RectItem


def mouse_down(canvas, x, y, button=Qt.MouseButton.MiddleButton):
    canvas.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(x, y), QPointF(x, y),
                                       button, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))


def mouse_up(canvas, x, y, button=Qt.MouseButton.MiddleButton):
    canvas.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(x, y), QPointF(x, y),
                                         button, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))


def make_canvas(qapp, w=160, h=120) -> AnnotationCanvas:
    canvas = AnnotationCanvas("test")
    canvas.resize(w, h)
    canvas.set_class_name("klass")
    canvas.load_frame(StreamFrame("s", synthetic_frame(), [], "k"), "klass")
    canvas.show()
    qapp.processEvents()
    return canvas


def test_zoom_around_cursor_keeps_image_point(qapp):
    canvas = make_canvas(qapp)
    before = canvas._to_image(QPointF(80, 60).toPoint() - canvas._image_origin())
    canvas.zoom_at(QPointF(80, 60).toPoint(), 2.0)
    after = canvas._to_image(QPointF(80, 60).toPoint() - canvas._image_origin())
    assert abs(before.x() - after.x()) <= 1 and abs(before.y() - after.y()) <= 1
    assert canvas._scale() > canvas._base_scale()


def test_zoom_clamped(qapp):
    canvas = make_canvas(qapp)
    for _ in range(20):
        canvas.zoom_at(QPointF(80, 60).toPoint(), 2.0)
    assert canvas._zoom == 5.0
    for _ in range(30):
        canvas.zoom_at(QPointF(80, 60).toPoint(), 0.5)
    assert canvas._zoom == 0.2


def test_middle_button_pans(qapp):
    canvas = make_canvas(qapp)
    origin_before = canvas._image_origin()
    mouse_down(canvas, 80, 60)
    canvas.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(130, 80), QPointF(130, 80),
                                      Qt.MouseButton.MiddleButton, Qt.MouseButton.MiddleButton,
                                      Qt.KeyboardModifier.NoModifier))
    mouse_up(canvas, 130, 80)
    assert canvas._image_origin().x() == origin_before.x() + 50
    assert canvas._image_origin().y() == origin_before.y() + 20


def test_annotations_use_image_coords_regardless_of_zoom(qapp):
    canvas = make_canvas(qapp)
    item = RectItem(10, 10, 40, 30, "klass")
    canvas.rects.append(item)
    canvas.selected = item
    canvas.zoom_at(QPointF(80, 60).toPoint(), 3.0)
    # mapping bild -> widget -> bild ar en identitet aven efter zoom och pan
    point = QPointF(12, 9).toPoint()
    widget_pos = canvas._to_widget(point) + canvas._image_origin()
    back = canvas._to_image(widget_pos - canvas._image_origin())
    assert abs(back.x() - point.x()) <= 1 and abs(back.y() - point.y()) <= 1
    # ritningen ar fortfarande i bildkoordinater: rektangeln oforandrad
    assert (item.rect.x(), item.rect.y()) == (10, 10)


def test_canvas_reset_view(qapp):
    canvas = make_canvas(qapp)
    canvas.zoom_at(QPointF(80, 60).toPoint(), 2.5)
    mouse_down(canvas, 80, 60)
    canvas.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(120, 70), QPointF(120, 70),
                                      Qt.MouseButton.MiddleButton, Qt.MouseButton.MiddleButton,
                                      Qt.KeyboardModifier.NoModifier))
    mouse_up(canvas, 120, 70)
    assert canvas._zoom != 1.0 or canvas._pan != QPointF(0, 0).toPoint()
    canvas.reset_view()
    assert canvas._zoom == 1.0
    assert canvas._image_origin() == canvas._base_origin()


def _make_view(qapp, tmp_path):
    from xray_detector.application.dataset_service import DatasetService
    from xray_detector.domain.config import AppConfig
    from PySide6.QtCore import QSettings

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    service = DatasetService(config.dataset_dir, config.classes)
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    view = AnnotationView(config, service, settings)
    return view, service


def test_draw_marks_dirty_and_save_clears(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    view, service = _make_view(qapp, tmp_path)
    canvas = view.canvases[0]
    view.load_captures([StreamFrame("l", synthetic_frame(), [], "k")])
    assert not view.is_dirty()
    canvas.set_selected_for_test = None
    # simulera en ritad rektangel via canvas dirty-markning
    canvas.rects.append(RectItem(5, 5, 30, 30, "klass"))
    canvas._mark_dirty()
    assert view.is_dirty()
    view._on_save()
    assert not view.is_dirty()
    assert service.current_version() >= 1
    assert service.metadata(service.current_version())["num_objects"] == 1


def test_save_without_boxes_asks_negative(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    view, service = _make_view(qapp, tmp_path)
    view.load_captures([StreamFrame("l", synthetic_frame(), [], "k")])
    view._on_save()
    info = service.metadata(service.current_version())
    assert info["num_images"] == 1
    assert info["num_objects"] == 0


def test_save_without_boxes_declined_writes_nothing(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    view, service = _make_view(qapp, tmp_path)
    view.load_captures([StreamFrame("l", synthetic_frame(), [], "k")])
    view._on_save()
    assert service.versions() == []


def test_tab_change_with_dirty_warns_and_can_revert(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel))
    from xray_detector.domain.config import AppConfig
    from xray_detector.ui.main_window import MainWindow

    config = AppConfig()
    config.data_dir = tmp_path
    config.ensure_dirs()
    window = MainWindow(config)
    window.annotation_view.load_captures([StreamFrame("l", synthetic_frame(), [], "k")])
    window.tabs.setTabEnabled(1, True)
    window.tabs.setCurrentIndex(1)
    canvas = window.annotation_view.canvases[0]
    canvas._mark_dirty()
    window.tabs.setCurrentIndex(0)  # försök byta flik med osparat
    assert window.tabs.currentIndex() == 1  # vakten vände tillbaka
    window.annotation_view.mark_clean()
    window.closeEvent(QCloseEvent())
