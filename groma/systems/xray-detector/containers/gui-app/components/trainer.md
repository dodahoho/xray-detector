---
type: C4 Component
title: Träningskörning
status: stable
groma:
  id: trainer
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/training/trainer.py
    - scanner: python
      file: xray_detector/infrastructure/training/trainer.py
    - scanner: python
      file: xray_detector/infrastructure/training/__init__.py
  group: Dataset och träning
description: QThread-wrapper som startar och bevakar träningsprocessen.
---

TrainConfig-dataklass och TrainingWorker (QThread) som kör "python -m xray_detector.training.train_task" som subprocess: skickar parametrar, lyssnar rad-för-rad på stdout som framstegssignaler, väntar på TRAINING_DONE och kan avbrytas med terminate(). Skriver vikter till models/v<version>/.
