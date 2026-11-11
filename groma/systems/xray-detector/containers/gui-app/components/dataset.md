---
type: C4 Component
title: Datasetlagring
status: stable
groma:
  id: dataset
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/dataset/store.py
    - scanner: python
      file: xray_detector/dataset/export.py
    - scanner: python
      file: xray_detector/infrastructure/dataset_store/store.py
    - scanner: python
      file: xray_detector/infrastructure/dataset_store/export.py
    - scanner: python
      file: xray_detector/infrastructure/dataset_store/__init__.py
  group: Dataset och träning
  technology: COCO JSON, PNG, YOLO-txt
description: COCO-dataset samt YOLO/COCO-export.
---

DatasetStore skriver bilder och annoteringar som en COCO-JSON (dataset.json) med metadata; bilder som sparats i samma annoteringssession får samma "group"-id (fångstgrupp) i datafilen. Ett dataset som sparades som v<N> flyttas upp till roten vid start. export_yolo, export_coco och export_rfdetr skriver träningsklara kataloger med manifest och tömmer katalogen först; rfdetr-exporten delar upp i train/valid/test med _annotations.coco.json per split. Kataloger under ~/.xray-detector.
