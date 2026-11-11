---
type: C4 Component
title: Annoteringsvy
status: stable
groma:
  id: annotation-view
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/annotation_view.py
  group: Användargränssnitt
description: Ritar och redigerar rektanglar med klass på frusna bilder.
---

Två AnnotationCanvas med handritad markering: ritning genom drag, flytt/storleksändring med riktade markörer, Delete-tangent, klasshantering (+/−) och sparning till dataset. Rektangeln får klass från komboboxen; rader utan klass får "objekt".

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/annotation_view.py](../../../../../../xray_detector/ui/annotation_view.py) | [xray_detector/dataset/store.py](../../../../../../xray_detector/dataset/store.py) | Sparar annoterade bilder | direkt anrop (add_samples) |
| [xray_detector/ui/annotation_view.py](../../../../../../xray_detector/ui/annotation_view.py) | [xray_detector/application/dataset_service.py](../../../../../../xray_detector/application/dataset_service.py) | Sparar annoterade bilder | direkt anrop |
| [xray_detector/ui/annotation_view.py](../../../../../../xray_detector/ui/annotation_view.py) | [xray_detector/ui/busy_indicator.py](../../../../../../xray_detector/ui/busy_indicator.py) | Visar upptagenindikator | Qt-widget |
| [xray_detector/ui/annotation_view.py](../../../../../../xray_detector/ui/annotation_view.py) | [xray_detector/application/background_task.py](../../../../../../xray_detector/application/background_task.py) | Sparar datasetet i bakgrunden | Qt-signaler |
| [xray_detector/ui/annotation_view.py](../../../../../../xray_detector/ui/annotation_view.py) | [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | Öppnar vyens inställningar | Qt-widget |
