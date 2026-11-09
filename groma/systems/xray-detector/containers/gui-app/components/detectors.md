---
type: C4 Component
title: Detektorer
status: stable
groma:
  id: detectors
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/detection/registry.py
    - scanner: python
      file: xray_detector/detection/base.py
    - scanner: python
      file: xray_detector/detection/yolo_detector.py
    - scanner: python
      file: xray_detector/detection/rfdetr_detector.py
    - scanner: python
      file: xray_detector/infrastructure/detectors/base.py
    - scanner: python
      file: xray_detector/infrastructure/detectors/yolo_detector.py
    - scanner: python
      file: xray_detector/infrastructure/detectors/rfdetr_detector.py
    - scanner: python
      file: xray_detector/infrastructure/detectors/__init__.py
  group: Video och detektion
  technology: ultralytics (YOLO26), rfdetr (valfritt), torch/CUDA
description: Detektionskontrakt och YOLO/RF-DETR-backends.
---

Infrastructure-lager för detektion: BaseDetector-ABC är det gemensamma kontraktet som kameratrådarna anropar per ram. YoloDetector kör ultralytics med CUDA->CPU-fallback (resolve_device) och enhetsetikett i GUI; RfDetrDetector är ett valfritt backend (rfdetr-paketet). Modellspecarna och fabriken (create_detector) ligger i applikationslagret (Modellregister).

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/detection/yolo_detector.py](../../../../../../xray_detector/detection/yolo_detector.py) | [ultralytics-yolo](../../../../../externals/ultralytics-yolo.md) | Kör YOLO-modell | YOLO.predict |
| [xray_detector/detection/rfdetr_detector.py](../../../../../../xray_detector/detection/rfdetr_detector.py) | [rf-detr](../../../../../externals/rf-detr.md) | Kör RF-DETR-modell | RFDETRBase.predict |
