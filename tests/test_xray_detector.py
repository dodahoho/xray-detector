from __future__ import annotations

import os
from datetime import datetime
import json
from pathlib import Path
import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from src.core.models_schema import (
    BoundingBox,
    CapturedFramePair,
    StreamFrameResult,
    TrainingConfig,
)
from src.core.scheduler import TrainingScheduler
from src.dataset.dataset_manager import DatasetManager
from src.ml.model_registry import ModelRegistry
from src.ui.annotation_canvas import AnnotationCanvas, EditableBoxItem
from src.ui.annotation_view import AnnotationView
from src.ui.detection_view import DetectionView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_bounding_box_conversions():
    box = BoundingBox(x1=100, y1=50, x2=300, y2=250, class_name="Metallföremål", confidence=0.9)
    assert box.width == 200
    assert box.height == 200
    assert box.to_coco_bbox() == [100.0, 50.0, 200.0, 200.0]

    yolo_bbox = box.to_yolo_bbox(img_width=1000, img_height=500)
    # x_center = 200/1000 = 0.2, y_center = 150/500 = 0.3, w = 200/1000 = 0.2, h = 200/500 = 0.4
    assert yolo_bbox == [0.2, 0.3, 0.2, 0.4]


def test_dataset_manager_and_coco_yolo_export(tmp_path: Path):
    working_dir = tmp_path / "working"
    exports_dir = tmp_path / "exports"
    dm = DatasetManager(working_dir=working_dir, exports_dir=exports_dir)

    img1 = np.zeros((480, 640, 3), dtype=np.uint8)
    img2 = np.zeros((480, 640, 3), dtype=np.uint8)
    boxes1 = [BoundingBox(10, 20, 110, 120, "Metallföremål", 0.95)]
    boxes2 = [
        BoundingBox(50, 60, 150, 180, "Batteri", 0.88),
        BoundingBox(200, 100, 280, 220, "NySpecialKlass", 1.0, is_manual=True),
    ]

    num_imgs, num_objs = dm.add_annotated_frame_pair(img1, boxes1, img2, boxes2)
    assert num_imgs == 2
    assert num_objs == 3
    assert "NySpecialKlass" in dm.get_classes()

    # Exportera version 1 i COCO+YOLO-format
    v1_info = dm.export_new_version(export_format="COCO+YOLO")
    assert v1_info.version == 1
    assert v1_info.num_images == 2
    assert v1_info.num_objects == 3
    assert v1_info.created_at != ""

    v1_dir = Path(v1_info.path)
    assert (v1_dir / "manifest.json").exists()
    assert (v1_dir / "annotations.coco.json").exists()
    assert (v1_dir / "data.yaml").exists()
    assert (v1_dir / "VERSION_INFO.txt").exists()

    with open(v1_dir / "annotations.coco.json", "r", encoding="utf-8") as f:
        coco = json.load(f)
    assert coco["info"]["version_number"] == 1
    assert coco["info"]["num_images"] == 2
    assert coco["info"]["num_objects"] == 3
    assert len(coco["annotations"]) == 3


def test_training_version_matches_dataset_version(tmp_path: Path):
    working_dir = tmp_path / "working"
    exports_dir = tmp_path / "exports"
    models_dir = tmp_path / "models"
    dm = DatasetManager(working_dir=working_dir, exports_dir=exports_dir)

    img = np.zeros((320, 320, 3), dtype=np.uint8)
    dm.add_annotated_frame_pair(
        img,
        [BoundingBox(20, 20, 100, 100, "Metallföremål")],
        img,
        [BoundingBox(40, 40, 120, 120, "Batteri")],
    )
    # Skapa v1 och sedan v2 så att vi verifierar att träning på v2 ger modellvikter med v2
    dm.export_new_version("COCO+YOLO")
    v2_info = dm.export_new_version("COCO+YOLO")
    assert v2_info.version == 2

    cfg = TrainingConfig(
        base_model_name="YOLO26-nano (Basmodell)",
        model_family="YOLO26",
        base_weights="yolo26n.pt",
        dataset_version=v2_info.version,
        dataset_path=v2_info.path,
        epochs=2,
        batch_size=2,
    )

    trainer = ModelRegistry.create_trainer("YOLO26")
    out_dir = models_dir / f"v{cfg.dataset_version}_yolo26"
    trained_info = trainer.train(
        config=cfg,
        output_dir=str(out_dir),
        progress_callback=lambda e, tot, m, log: None,
        stop_requested=lambda: False,
    )

    assert trained_info.version == 2
    assert trained_info.dataset_version == 2
    assert Path(trained_info.weights_path).exists()

    registry = ModelRegistry(models_dir=models_dir)
    listed = registry.list_trained_models()
    assert len(listed) == 1
    assert listed[0].version == 2


def test_detection_to_annotation_and_box_resizing(qapp, tmp_path: Path):
    det_view = DetectionView()
    frame1 = np.full((480, 640, 3), 200, dtype=np.uint8)
    frame2 = np.full((480, 640, 3), 210, dtype=np.uint8)

    box1 = BoundingBox(50, 60, 150, 160, "Metallföremål", 0.91)
    box2 = BoundingBox(100, 120, 220, 240, "Batteri", 0.87)

    res1 = StreamFrameResult(stream_id=1, stream_name="Ström 1", frame_bgr=frame1, detections=[box1], fps=30.0)
    res2 = StreamFrameResult(stream_id=2, stream_name="Ström 2", frame_bgr=frame2, detections=[box2], fps=30.0)
    det_view.update_frames(res1, res2)

    captured_pairs = []
    det_view.capture_requested.connect(lambda p: captured_pairs.append(p))
    det_view.trigger_capture()

    assert len(captured_pairs) == 1
    pair: CapturedFramePair = captured_pairs[0]
    assert len(pair.stream_1_boxes) == 1
    assert len(pair.stream_2_boxes) == 1

    # Ladda in i AnnotationView och kontrollera att befintliga detektioner ritas in automatiskt
    dm = DatasetManager(working_dir=tmp_path / "work", exports_dir=tmp_path / "exp")
    ann_view = AnnotationView(dataset_manager=dm)
    ann_view.load_captured_pair(pair)

    items_1 = ann_view.canvas_1.get_box_items()
    items_2 = ann_view.canvas_2.get_box_items()
    assert len(items_1) == 1
    assert len(items_2) == 1

    # Testa att greppunkterna (hörn och kant) på EditableBoxItem identifieras korrekt
    item = items_1[0]
    assert item._hit_test_handle(QPointF(50, 60)) == EditableBoxItem.HANDLE_TOP_LEFT
    assert item._hit_test_handle(QPointF(150, 160)) == EditableBoxItem.HANDLE_BOTTOM_RIGHT
    assert item._hit_test_handle(QPointF(100, 60)) == EditableBoxItem.HANDLE_TOP
    assert item._hit_test_handle(QPointF(150, 110)) == EditableBoxItem.HANDLE_RIGHT

    # Testa att byta klass och lägga till en helt ny klass
    ann_view._on_canvas_box_selected(1, item)
    ann_view.new_class_input.setText("Kretskort")
    ann_view._on_add_new_class()
    assert item.class_name == "Kretskort"
    assert "Kretskort" in dm.get_classes()

    # Spara i annoteringsläget -> fyller på dataset och signalerar återgång till detektionsläge
    returned = []
    ann_view.saved_and_return.connect(lambda: returned.append(True))
    ann_view.save_and_return_to_detection()
    assert len(returned) == 1
    assert dm.get_working_stats() == (2, 2)


def test_scheduler_night_and_inactivity(qapp):
    scheduler = TrainingScheduler(
        inactivity_timeout_minutes=10,
        night_start_str="23:00",
        night_end_str="05:00",
    )
    assert scheduler.is_night_window(datetime(2026, 11, 3, 23, 30)) is True
    assert scheduler.is_night_window(datetime(2026, 11, 4, 2, 15)) is True
    assert scheduler.is_night_window(datetime(2026, 11, 3, 14, 0)) is False
