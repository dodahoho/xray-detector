---
type: C4 Component
title: Epoch metrics
status: stable
groma:
  id: epoch-metrics
  parent: training-process
  code:
    - scanner: python
      file: xray_detector/infrastructure/training/epoch_metrics.py
description: Epokvisa träningsvärden ur metrics-filerna.
---

Ultralytics skriver results.csv och RF-DETR metrics.csv, en rad per loggning. Modulen läser de rader som tillkommit sedan förra läsningen, bygger ett EpochMetrics per epok och skickar det som en EPOCH {json}-rad på stdout. GUI:t parsar raden i stället för att tolka fri text, och slipper bry sig om vilken familj som tränar. MetricsTail hanterar att Lightning skriver om filen när en kolumn tillkommer.
