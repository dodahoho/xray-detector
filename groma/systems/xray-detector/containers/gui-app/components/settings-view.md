---
type: C4 Component
title: Inställningsflik
status: stable
groma:
  id: settings-view
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/settings_view.py
  group: Användargränssnitt
description: 'Applikationens globala inställningar: temat och modellistan.'
---

Fliken håller sådant som inte hör till någon av de andra flikarna. Den komponerar ThemeSection från settings_dialog.py, så temat byts på samma ställe oavsett vilken vy användaren arbetar i, och ModelSection från model_settings.py, som listar modellerna och låter användaren lägga till, byta namn på och ta bort dem. Korten håller sig till vänster i vyn, så fälten inte växer över skärmen. Vyernas egna inställningar ligger i respektive vys inställningsknapp.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/settings_view.py](../../../../../../xray_detector/ui/settings_view.py) | [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | Visar globala inställningar | Qt-widget |
| [xray_detector/ui/settings_view.py](../../../../../../xray_detector/ui/settings_view.py) | [xray_detector/ui/model_settings.py](../../../../../../xray_detector/ui/model_settings.py) | Visar modellistan | Qt-widget |
