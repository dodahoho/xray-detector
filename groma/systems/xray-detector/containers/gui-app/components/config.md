---
type: C4 Component
title: Konfiguration
status: stable
groma:
  id: config
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/config.py
    - scanner: python
      file: xray_detector/domain/config.py
description: 'Appens standardvärden: klasser, datkataloger och trösklar.'
---

AppConfig-dataclass med defaultklasser (cigaretter, cannabis, kniv, pistol) och sökvägar under ~/.xray-detector (datasets, exports, models). Bärbar runtime-konfiguration saknas; GUI-justerbara värden persistas i QSettings istället.
