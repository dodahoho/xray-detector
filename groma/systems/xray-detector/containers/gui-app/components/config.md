---
type: C4 Component
title: Konfiguration
status: stable
groma:
  id: config
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/domain/config.py
description: 'Appens standardvärden: klasser, datakataloger och trösklar.'
---

AppConfig-dataclass med defaultklasser (cigaretter, cannabis, kniv, pistol), trösklar och sökvägar. Dataset, exporter och inställningar ligger under ~/.xray-detector (data_dir), medan models_dir och logs_dir räknas ut ur paketets placering och därför pekar på projektets models/ och logs/ oavsett arbetskatalog. Båda går att peka om i config.yaml. ensure_dirs() skapar alla kataloger vid behov. Bärbar runtime-konfiguration saknas; GUI-justerbara värden persistas i QSettings istället.
