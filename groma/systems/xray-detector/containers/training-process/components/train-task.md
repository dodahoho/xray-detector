---
type: C4 Component
title: Tränings-CLI
status: stable
groma:
  id: train-task
  parent: training-process
  code:
    - scanner: python
      file: xray_detector/training/train_task.py
      symbol: main
    - scanner: python
      file: xray_detector/infrastructure/training/train_task.py
      symbol: main
description: Själva YOLO-träningen i egen process.
---

Argparse-CLI som körs som modul: laddar YOLO-vikter, tränar på exporterat data.yaml (epochs, imgsz, batch) på CUDA med CPU-fallback via resolve_device och skriver ut TRAINING_DONE på sista raden. Endast YOLO-träning är implementerad (RF-DETR-träning finns ej).

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/training/train_task.py](../../../../../../xray_detector/training/train_task.py) | [xray_detector/detection/yolo_detector.py](../../../../../../xray_detector/detection/yolo_detector.py) | Återanvänder enhetsval | import |
| [xray_detector/training/train_task.py](../../../../../../xray_detector/training/train_task.py) | [ultralytics-yolo](../../../../../externals/ultralytics-yolo.md) | Tränar YOLO-modell | YOLO.train |
