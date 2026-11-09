---
type: C4 Component
title: Datasetservice
status: stable
groma:
  id: dataset-service
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/dataset_service.py
    - scanner: python
      file: xray_detector/application/__init__.py
  group: Dataset och träning
description: 'Fasad över datasetlagringen: versioner, sparade bilder, radering och export.'
---

Applikationslagrets gränssnitt mot DatasetStore och export: klasserna annoterings/sparning kallar add_samples, datasetvyn listar/raderar via versions/load_coco/delete_images, träningsvyn exporterar YOLO/COCO. UI:t berör aldrig lagringsmodulerna direkt.
