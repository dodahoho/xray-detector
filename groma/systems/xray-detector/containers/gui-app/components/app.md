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

Bygger QApplication, filtrerar DirectWrite-typsnittsvarningen, laddar AppConfig och visar MainWindow (maximerat första gången, därefter sparad fönstergeometri via QSettings). Direkt efter QApplication anropas install_swedish_translations(), så Qt:s egna standardknappar blir svenska redan i första fönstret. Sätter applikationsikonen från ui/assets/app.ico på QApplication, vilket ger fönstret både ICON_SMALL och ICON_BIG, och ger processen en egen AppUserModelID innan första fönstret skapas. Utan den identiteten grupperar Windows fönstret under python.exe och ritar Python-ikonen i aktivitetsfältet, oavsett vilken ikon Qt sätter på fönstret.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/app.py](../../../../../../xray_detector/app.py) | [xray_detector/config.py](../../../../../../xray_detector/config.py) | Läser standardkonfiguration | import |
| [xray_detector/app.py](../../../../../../xray_detector/app.py) | [xray_detector/ui/main_window.py](../../../../../../xray_detector/ui/main_window.py) | Skapar huvudfönstret | direkt anrop |
| [xray_detector/app.py](../../../../../../xray_detector/app.py) | [xray_detector/ui/translations.py](../../../../../../xray_detector/ui/translations.py) | Installerar svensk översättning | direkt anrop |
