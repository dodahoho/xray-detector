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
      file: xray_detector/detection/__init__.py
  group: Video och detektion
  technology: ultralytics (YOLO26), rfdetr (valfritt), torch/CUDA
description: Detektionsgränssnitt, modellregister och YOLO/RF-DETR-backends.
---

BaseDetector-ABC + Detection-dataclass är gemensamt kontrakt. MODEL_SPECS-registret listar YOLO26 n/s/m och RF-DETR base; create_detector() bygger vald backend från spec. YoloDetector använder ultralytics med CUDA→CPU-fallback (resolve_device) och visas med enhetsetikett i GUI; RfDetrDetector är ett valfritt backend (rfdetr-paketet).

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/detection/yolo_detector.py](../../../../../../xray_detector/detection/yolo_detector.py) | [ultralytics-yolo](../../../../../externals/ultralytics-yolo.md) | Kör YOLO-modell | YOLO.predict |
| [xray_detector/detection/rfdetr_detector.py](../../../../../../xray_detector/detection/rfdetr_detector.py) | [rf-detr](../../../../../externals/rf-detr.md) | Kör RF-DETR-modell | RFDETRBase.predict |
