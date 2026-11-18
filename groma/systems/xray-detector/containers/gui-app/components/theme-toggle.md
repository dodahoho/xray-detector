---
type: C4 Component
title: Theme toggle
status: stable
groma:
  id: theme-toggle
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/theme_toggle.py
description: Ikonknapp som växlar mellan ljust och mörkt tema.
---

Knappen ligger till höger om vyernas inställningsknapp. Ikonen visar vad ett klick gör: en grå sol i mörkt läge och en grå måne i ljust läge. Alla knappar lyssnar på samma signal, så en växling slår igenom i alla vyer på en gång. Första klicket väljer motsatsen till den palett som syns, så även systemtemat hamnar i ljust eller mörkt.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/theme_toggle.py](../../../../../../xray_detector/ui/theme_toggle.py) | [xray_detector/ui/theme.py](../../../../../../xray_detector/ui/theme.py) | Växlar och sparar temat | funktionsanrop |
