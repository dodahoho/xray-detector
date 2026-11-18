---
type: C4 Component
title: Progress
status: stable
groma:
  id: progress
  parent: training-process
  code:
    - scanner: python
      file: xray_detector/infrastructure/training/progress.py
description: Förlopp inom pågående epok.
---

Epokeventet kommer först när epoken är klar, så en epok som tar flera minuter ser ut som en hängning. Modulen skriver en PROGRESS {json}-rad med jämna mellanrum under epoken, i linje med EPOCH-raden, så träningsvyn slipper tolka fri text. Skrivningarna är throttlade till en rad per intervall.
