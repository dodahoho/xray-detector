---
type: C4 Component
title: Metrics
status: stable
groma:
  id: metrics
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/training/metrics.py
description: mAP och falsklarm för en tränad detektor.
---

Rena funktioner på numpy-arrayer, så de går att testa utan GPU, torch eller en modell. Modulen känner inte till YOLO eller RF-DETR: den får förutsägelser och facit per bild och räknar ut samma tal som utvärderingsrapporten visar. iou_matrix används också av utjämningen mellan ramar.
