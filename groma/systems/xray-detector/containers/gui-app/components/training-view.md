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

Val av basmodell (YOLO26 nano/small/medium eller RF-DETR nano/small/medium/large), epoker, bildstorlek och batch, med en sammanställning av datasetet ovanför. Starten exporterar datasetet i den familj modellen tillhör — YOLO till train.txt/val.txt med data.yaml, RF-DETR till train/valid/test — i en bakgrundsuppgift och startar TrainingWorker först när data.yaml finns; ett schemalagt jobb exporterar i stället när villkoret är uppfyllt, så det tränar på aktuella annoteringar. Loggen visar processens stdout-rad för rad och detektionen pausas under träning. Varje rad skrivs också till logs/training.log via file_logger(), med en rubrikrad per körning (tidsstämpel, basmodell, dataset och körningskatalog) så avslutade och avbrutna körningar går att skilja åt efteråt.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/training/trainer.py](../../../../../../xray_detector/training/trainer.py) | Startar träningsjobb | QThread |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/application/training_service.py](../../../../../../xray_detector/application/training_service.py) | Startar träningsjobb | direkt anrop |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/ui/busy_indicator.py](../../../../../../xray_detector/ui/busy_indicator.py) | Visar upptagenindikator | Qt-widget |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/application/background_task.py](../../../../../../xray_detector/application/background_task.py) | Exporterar i bakgrunden | Qt-signaler |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | Öppnar vyens inställningar | Qt-widget |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/dataset/export.py](../../../../../../xray_detector/dataset/export.py) | Exporterar datasetet när träningen startar | direkt anrop |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/infrastructure/dataset_store/export.py](../../../../../../xray_detector/infrastructure/dataset_store/export.py) | Exporterar datasetet vid start | direkt anrop |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/infrastructure/training/trainer.py](../../../../../../xray_detector/infrastructure/training/trainer.py) | Startar träningsjobb | direkt anrop |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/infrastructure/dataset_store/store.py](../../../../../../xray_detector/infrastructure/dataset_store/store.py) | Läser datasetet | direkt anrop |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/ui/model_combo.py](../../../../../../xray_detector/ui/model_combo.py) | Visar modellväljaren | Qt-widget |
| [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | [xray_detector/ui/theme_toggle.py](../../../../../../xray_detector/ui/theme_toggle.py) | Visar temaväxlaren | Qt-widget |
