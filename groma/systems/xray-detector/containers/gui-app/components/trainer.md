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
description: Startar och bevakar träningsprocessen via QProcess.
---

TrainingWorker är en QObject som startar träningsprocessen som en separat OS-process via QProcess och strömmar dess stdout radvis som progress-signaler. Kommandoraden byggs av TrainConfig (dataset, vikter, output, epoker, bildstorlek, batch och familj) och kan läsas ut med command() för test. cancel() avbryter med terminate() och kill()-fallback så inga föräldralösa processer lämnas kvar efter appen. Vikterna hamnar under models/v<version>/.
