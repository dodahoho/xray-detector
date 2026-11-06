---
type: C4 Actor
title: Säkerhetsoperatör
status: stable
groma:
  id: säkerhetsoperatör
---

Person som bevakar röntgenvideo i realtid, fångar misstänkta bilder, annoterar dem med klass och position, och tränar om modeller när datasetet växt.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [säkerhetsoperatör](s%C3%A4kerhetsoperat%C3%B6r.md) | [xray_detector/app.py](../../xray_detector/app.py) | Startar och använder appen | PySide6 GUI |
| [säkerhetsoperatör](s%C3%A4kerhetsoperat%C3%B6r.md) | [xray_detector/ui/detection_view.py](../../xray_detector/ui/detection_view.py) | Bevakar strömmar och fångar bilder | PySide6 GUI |
| [säkerhetsoperatör](s%C3%A4kerhetsoperat%C3%B6r.md) | [xray_detector/ui/annotation_view.py](../../xray_detector/ui/annotation_view.py) | Ritar och redigerar annoteringar | PySide6 GUI |
| [säkerhetsoperatör](s%C3%A4kerhetsoperat%C3%B6r.md) | [xray_detector/ui/training_view.py](../../xray_detector/ui/training_view.py) | Startar modellträning | PySide6 GUI |
