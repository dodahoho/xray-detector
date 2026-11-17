"""De delade hjälparna i ui/ och IoU-implementationen (TASK-140)."""

import numpy as np
import pytest

from xray_detector.application.model_registry import ModelSpec
from xray_detector.domain.detection import Detection
from xray_detector.infrastructure.detectors.smoothing import _iou
from xray_detector.infrastructure.training.metrics import iou_matrix
from xray_detector.ui.image_utils import bgr_to_qimage
from xray_detector.ui.model_combo import ModelComboBox


def test_bgr_to_qimage_owns_its_pixels(qapp):
    """Kopian överlever anropet, så QImage inte pekar på en frigjord array."""
    frame = np.full((8, 8, 3), 200, dtype=np.uint8)

    image = bgr_to_qimage(frame)
    frame[:] = 0

    assert image.pixelColor(0, 0).red() == 200


def test_bgr_to_qimage_swaps_the_channels(qapp):
    """BGR-blått blir RGB-blått."""
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    frame[:, :, 0] = 255  # blå i BGR

    image = bgr_to_qimage(frame)

    assert image.pixelColor(0, 0).blue() == 255
    assert image.pixelColor(0, 0).red() == 0


def _specs() -> list[ModelSpec]:
    return [
        ModelSpec(key="yolo26n", label="YOLO26 nano", family="yolo", weights="yolo26n.pt"),
        ModelSpec(key="rfdetr-nano", label="RF-DETR nano", family="rfdetr", weights="nano"),
    ]


def test_model_combo_fills_and_keeps_the_selection(qapp):
    combo = ModelComboBox()
    combo.fill(_specs(), "yolo26n")

    assert [combo.itemData(row) for row in range(combo.count())] == [
        "yolo26n",
        "rfdetr-nano",
    ]
    assert combo.currentData() == "yolo26n"
    assert combo.spec().key == "yolo26n"

    combo.fill(_specs(), "rfdetr-nano")

    assert combo.currentData() == "rfdetr-nano"


def test_model_combo_disables_a_missing_package(qapp, monkeypatch):
    """Saknat rfdetr-paket stänger av posten och märker texten (TASK-140)."""
    import xray_detector.ui.model_combo as model_combo

    monkeypatch.setattr(model_combo, "missing_packages", lambda: {"rfdetr": True})
    combo = ModelComboBox()

    combo.fill(_specs(), "yolo26n")

    rfdetr_row = combo.findData("rfdetr-nano")
    assert not combo.enabled(rfdetr_row)
    assert "(rfdetr ej installerat)" in combo.itemText(rfdetr_row)
    assert combo.enabled(combo.findData("yolo26n"))


def test_smoothing_uses_the_shared_iou():
    """Smoothingens IoU är metrics-svitens, inte en egen kopia (TASK-140)."""
    detection = Detection(0.0, 0.0, 10.0, 10.0, "kniv", 0.9)
    box = [5.0, 5.0, 15.0, 15.0]

    expected = float(iou_matrix([box], [[0.0, 0.0, 10.0, 10.0]])[0][0])

    assert _iou(box, detection) == pytest.approx(expected)
    assert _iou(box, detection) == pytest.approx(25 / 175)
