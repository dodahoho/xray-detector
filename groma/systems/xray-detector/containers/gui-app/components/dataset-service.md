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
description: 'Fasad över datasetlagringen: sparade bilder, radering och export.'
---

Applikationslagrets gränssnitt mot DatasetStore och export: annoteringsvyn sparar via add_samples, datasetvyn listar och raderar via load_dataset/delete_images, träningsvyn exporterar YOLO, COCO eller RF-DETR. load_dataset returnerar klasserna och bilderna med annoteringar som klassnamn och pixel-bboxar, så vyerna slipper känna till YOLO-formatet. UI:t berör aldrig lagringsmodulerna direkt.
