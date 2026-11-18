---
type: C4 Component
title: Training history
status: stable
groma:
  id: training-history
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/training_history.py
description: Läser tidigare träningars manifest och exporterar modeller.
---

Varje träningskörning beskrivs av sitt training_manifest.json under models/trained/. Modulen läser dem till TrainingRun, läser epokhistoriken ur körningens metrics-fil och kopierar en vald körnings vikter och manifest till en katalog användaren väljer.
