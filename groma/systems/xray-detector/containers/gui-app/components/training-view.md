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

Val av basmodell (YOLO26 nano/small/medium eller RF-DETR nano/small/medium/large), datasetversion, epoker, bildstorlek och batch. Starten exporterar datasetet i den familj modellen tillhör — YOLO till data.yaml, RF-DETR till train/valid/test — och startar TrainingWorker; loggen visar processens stdout-rad för rad och detektionen pausas under träning. Egna knappar exporterar datasetversionen till COCO eller YOLO utan att starta träning.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/dataset/export.py](../../../../../../xray_detector/dataset/export.py) | Exporterar YOLO-dataset | direkt anrop |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/training/trainer.py](../../../../../../xray_detector/training/trainer.py) | Startar träningsjobb | QThread |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/application/training_service.py](../../../../../../xray_detector/application/training_service.py) | Startar träningsjobb | direkt anrop |
