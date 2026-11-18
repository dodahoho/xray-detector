---
type: C4 Component
title: Model input
status: stable
groma:
  id: model-input
  parent: xray-detector
  code:
    - scanner: python
      file: xray_detector/domain/model_input.py
      symbol: round_size
description: Modellens indatastorlek i pixlar.
---

STEP, MIN_SIZE, MAX_SIZE och DEFAULT_SIZE samt round_size(), som avrundar uppåt till närmaste multipel av 32 inom [320, 1920]. Delas av inferensen (yolo_detector) och träningen (train_task, training_view), så de två vägarna inte kan glida isär.
