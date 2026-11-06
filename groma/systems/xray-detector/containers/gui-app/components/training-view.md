---
type: C4 Component
title: Träningsvy
status: stable
groma:
  id: training-view
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/training_view.py
  group: Användargränssnitt
description: Konfigurerar och startar modellträning.
---

Val av basmodell (YOLO26 n/s/m, RF-DETR), datasetversion, epoker, bildstorlek och batch. Starten exporterar YOLO-datasetet och startar TrainingWorker; loggen visar processens stdout-rad för rad; detektionen pausas under träning.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/dataset/export.py](../../../../../../xray_detector/dataset/export.py) | Exporterar YOLO-dataset | direkt anrop |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/training/trainer.py](../../../../../../xray_detector/training/trainer.py) | Startar träningsjobb | QThread |
