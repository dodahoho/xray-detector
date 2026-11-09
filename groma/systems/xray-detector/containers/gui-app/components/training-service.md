---
type: C4 Component
title: Träningstjänst
status: stable
groma:
  id: training-service
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/training_service.py
  group: Dataset och träning
description: Skapar och avbryter träningsjobb (TrainingWorker).
---

Applikationslagrets fasad över träningsprocessen: create_worker(TrainConfig) bygger en TrainingWorker som kör tränings-CLI:n i delprocess, cancel() avbryter aktivt jobb.
