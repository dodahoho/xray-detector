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
description: Applikationens globala inställningar, i dag temat.
---

Fliken håller sådant som inte hör till någon av de andra flikarna. Den komponerar ThemeSection från settings_dialog.py, så temat byts på samma ställe oavsett vilken vy användaren arbetar i. Vyernas egna inställningar ligger i respektive vys inställningsknapp.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/settings_view.py](../../../../../../xray_detector/ui/settings_view.py) | [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | Visar globala inställningar | Qt-widget |
