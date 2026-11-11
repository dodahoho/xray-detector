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
description: Tränar YOLO- eller RF-DETR-modellen i egen process.
---

Argparse-CLI som körs som modul: väljer familj med --family (yolo eller rfdetr), laddar basvikterna och tränar på exporterat dataset på CUDA med CPU-fallback via resolve_device. YOLO tränas med ultralytics på data.yaml; RF-DETR tränas på det exporterade rfdetr-datasetet med vald storlek, och kwargs filtreras mot paketets faktiska train()-signatur eftersom den varierar mellan versioner. Efter träningen skrivs training_manifest.json med basvikter, klasser, epoker och metrics, och TRAINING_DONE skrivs på sista raden.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/training/train_task.py](../../../../../../xray_detector/training/train_task.py) | [xray_detector/detection/yolo_detector.py](../../../../../../xray_detector/detection/yolo_detector.py) | Återanvänder enhetsval | import |
| [xray_detector/training/train_task.py](../../../../../../xray_detector/training/train_task.py) | [ultralytics-yolo](../../../../../externals/ultralytics-yolo.md) | Tränar YOLO-modell | YOLO.train |
