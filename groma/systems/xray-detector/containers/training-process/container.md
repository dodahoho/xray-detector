---
type: C4 Container
title: Träningsprocess (CLI)
status: stable
groma:
  id: training-process
  parent: xray-detector
  technology: Python CLI, ultralytics
description: Fristående process som tränar en YOLO-modell på exporterat dataset.
---

Körs som "python -m xray_detector.training.train_task" av TrainingWorker i GUI-processen. Läser dataset/weights/epochs-parametrar på kommandoraden, väljer CUDA med CPU-fallback via resolve_device, tränar med ultralytics YOLO och skriver ut TRAINING_DONE vid lyckat slut; GUI-processen bevakar stdout-raderna som framsteg.
