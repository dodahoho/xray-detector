---
type: C4 Component
title: Programstart
status: stable
groma:
  id: app
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/app.py
    - scanner: python
      file: xray_detector/__init__.py
description: Startar GUI-processen och skapar huvudfönstret.
---

Bygger QApplication, filtrerar DirectWrite-typsnittsvarningen, laddar AppConfig och visar MainWindow (maximerat första gången, därefter sparad fönstergeometri via QSettings).

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/app.py](../../../../../../xray_detector/app.py) | [xray_detector/config.py](../../../../../../xray_detector/config.py) | Läser standardkonfiguration | import |
| [xray_detector/app.py](../../../../../../xray_detector/app.py) | [xray_detector/ui/main_window.py](../../../../../../xray_detector/ui/main_window.py) | Skapar huvudfönstret | direkt anrop |
