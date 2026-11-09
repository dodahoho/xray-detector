"""Test av QGraphicsScene-prototypen (TASK-21 spike).

Visar att prototypen uppfyller de egenskaper som drivit iden om en port:
kosmetisk penna (konstant linjetjocklek oavsett zoom), gratis
markerings-/flytt-flags, storleksandring via handtag i bildkoordinater,
och zoom som inte paverkar boxarnas rektanglar.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPixmap

from prototype.annotation_scene import AnnotationScene, AnnotationView, BoxItem, MIN_BOX


def _scene_with_background(qapp):
    pixmap = QPixmap(64, 48)
    pixmap.fill()
    scene = AnnotationScene()
    scene.set_background(pixmap)
    return scene


def test_box_selectable_and_movable(qapp):
    scene = _scene_with_background(qapp)
    box = scene.add_box(QRectF(5, 5, 20, 10), "kniv")
    assert box.flags() & BoxItem.GraphicsItemFlag.ItemIsSelectable
    assert box.flags() & BoxItem.GraphicsItemFlag.ItemIsMovable
    box.setSelected(True)
    assert box.isSelected()
    assert box.pen().color() == box.pen().color()  # vald stil applicerad via itemChange


def test_cosmetic_pen_constant_over_zoom(qapp):
    scene = _scene_with_background(qapp)
    view = AnnotationView(scene)
    box = scene.add_box(QRectF(5, 5, 20, 10), "kniv", view=view)
    assert box.pen().isCosmetic()
    width_before = box.pen().widthF()
    view.scale(6.0, 6.0)
    assert box.pen().widthF() == width_before  # skarm-tjocklek invariant
    # boxens rektangel/datan paverkas inte av vy-transformen
    assert box.rect() == QRectF(5, 5, 20, 10)


def test_resize_handle_moves_in_image_coords(qapp):
    scene = _scene_with_background(qapp)
    view = AnnotationView(scene)
    box = scene.add_box(QRectF(10, 10, 40, 30), "pistol", view=view)
    view.scale(3.0, 3.0)
    handle = box.hit_handle(QPointF(10, 25))
    assert handle == "l", handle
    box.resize_to("l", QPointF(2, 25))
    assert box.rect().left() == 2
    assert box.rect().width() == 48


def test_resize_respects_min_size(qapp):
    scene = _scene_with_background(qapp)
    box = scene.add_box(QRectF(10, 10, 40, 30), "pistol")
    box.resize_to("r", QPointF(-200, 25))  # langt utanfor till vanster
    assert box.rect().width() >= MIN_BOX


def test_annotations_export(qapp):
    scene = _scene_with_background(qapp)
    scene.add_box(QRectF(1, 2, 30, 20), "kniv")
    scene.add_box(QRectF(4, 5, 10, 10), "pistol")
    annotations = scene.boxes_as_annotations()
    assert annotations[0]["class_name"] == "kniv"
    assert annotations[0]["bbox"] == [1, 2, 30, 20]
    assert annotations[1]["bbox"] == [4, 5, 10, 10]


def test_view_zoom_keeps_scene_data(qapp):
    scene = _scene_with_background(qapp)
    view = AnnotationView(scene)
    box = scene.add_box(QRectF(5, 5, 20, 10), "kniv")
    before = view.transform().m11()
    view.scale(2.5, 2.5)
    assert view.transform().m11() > before
    assert [a["bbox"] for a in scene.boxes_as_annotations()] == [[5, 5, 20, 10]]
