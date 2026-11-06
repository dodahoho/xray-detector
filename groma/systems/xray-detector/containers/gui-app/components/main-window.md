---
type: C4 Component
title: Huvudfönster
status: stable
groma:
  id: main-window
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/main_window.py
    - scanner: python
      file: xray_detector/ui/__init__.py
  group: Användargränssnitt
description: Bygger flikarna och dirigerar flödet mellan vyerna.
---

QMainWindow med flikarna Detektion, Annotation, Dataset, Träning och Inställningar. Wiring: fångade bilder till annotering, sparade annoteringar uppdaterar datasetvyn, träning pausar/återupptar detektion, F11 växlar fullskärm, inställningar persistas vid stängning (fönstergeometri, modell, källor, träningsparametrar, tema).

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/main_window.py](../../../../../../xray_detector/ui/main_window.py) | [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | Arrangerar som flik | direkt anrop |
| [xray_detector/ui/main_window.py](../../../../../../xray_detector/ui/main_window.py) | [xray_detector/ui/annotation_view.py](../../../../../../xray_detector/ui/annotation_view.py) | Laddar fångade bilder | direkt metodanrop |
| [xray_detector/ui/main_window.py](../../../../../../xray_detector/ui/main_window.py) | [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | Uppdaterar efter sparad annotering | direkt metodanrop |
| [xray_detector/ui/main_window.py](../../../../../../xray_detector/ui/main_window.py) | [xray_detector/ui/training_view.py](../../../../../../xray_detector/ui/training_view.py) | Pausar och återupptar detektion | Qt-signaler |
| [xray_detector/ui/main_window.py](../../../../../../xray_detector/ui/main_window.py) | [xray_detector/ui/theme.py](../../../../../../xray_detector/ui/theme.py) | Applicerar sparat tema | funktionsanrop |
