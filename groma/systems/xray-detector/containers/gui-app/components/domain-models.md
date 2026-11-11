---
type: C4 Component
title: Domänmodeller
status: stable
groma:
  id: domain-models
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/domain/capture.py
      symbol: StreamFrame
    - scanner: python
      file: xray_detector/domain/detection.py
    - scanner: python
      file: xray_detector/domain/dataset.py
      symbol: AnnotatedImage
    - scanner: python
      file: xray_detector/domain/training.py
      symbol: TrainConfig
    - scanner: python
      file: xray_detector/domain/__init__.py
description: 'Rena dataklasser som båda lagren delar: kantdata utan GUI- eller bildbibliotek.'
---

Domänlagret i den lagerindelade arkitekturen (TASK-22): Detection (rektangeln med klass och säkerhet), StreamFrame (ram + detektioner per ström), AnnotatedImage (bild + annoteringar vid sparning), TrainConfig (träningsparametrar) samt AppConfig (klasser, datakataloger, trösklar). Importerar enbart numpy/pathlib - inga Qt-, OpenCV- eller torch-beroenden, vilket gör lagret testbart isolerat.
