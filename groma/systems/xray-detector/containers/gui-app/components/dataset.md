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
description: Versionshanterade COCO-dataset samt YOLO/COCO-export.
---

DatasetStore skriver bilder och annoteringar som COCO-JSON per version (v1, v2, ...) med metadata; bilder som sparats i samma annoteringssession får samma "group"-id (fångstgrupp) i datafilen. export_yolo, export_coco och export_rfdetr skriver träningsklara kataloger med manifest; rfdetr-exporten delar upp i train/valid/test med `_annotations.coco.json` per split. Kataloger under ~/.xray-detector.
