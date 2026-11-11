---
type: C4 Component
title: Detektionsutjämning
status: stable
groma:
  id: detectors-smoothing
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/detectors/smoothing.py
description: Jämnar ut detektioner mellan ramar med EMA och hysteres.
---

DetectionSmoother matchar varje ny detektion mot en spårad ruta med IoU, jämnar ut position och storlek med EMA och kräver två träffar innan en ruta visas. En ruta släcks först efter tre missade ramar. Utan utjämningen fladdrar overlayn när modellen varierar några pixlar mellan ramar eller en detektion ligger nära confidence-tröskeln. CameraService håller en egen smoother per ström.
