---
type: C4 Component
title: Inferenstrådar
status: stable
groma:
  id: detectors-tuning
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/detectors/tuning.py
      symbol: configure_inference_threads
description: Begränsar torch och OpenCV till en CPU-tråd när GPU-inferensen körs.
---

Inferensen går på GPU, men letterbox, normalisering och NMS sker på CPU, och PyTorch sprider de små tensorerna över alla kärnor som standard. Med CUDA tillgängligt sätts torch.set_num_threads(1) och OpenCV:s trådar till en, vilket mätt sänkte RF-DETR small från cirka 2200 % till cirka 100 % CPU utan att bildfrekvensen ändrades. Utan CUDA lämnas inställningarna orörda, där vinner flera trådar. Anropas en gång per detektor från YOLO- och RF-DETR-backenderna.
