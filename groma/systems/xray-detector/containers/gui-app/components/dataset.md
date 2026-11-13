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
    - scanner: python
      file: xray_detector/infrastructure/dataset_store/yolo.py
  group: Dataset och träning
  technology: YOLO (data.yaml, PNG, txt), JSON-metadata
description: YOLO-dataset samt YOLO/COCO/RF-DETR-export.
---

DatasetStore lagrar datasetet i YOLO-format: klasserna i data.yaml, bilderna i images/ och annoteringarna i labels/ (en .txt per bild med klassindex och normaliserade mått). dataset.json innehåller bara metadata som YOLO saknar: bild-id, bildstorlek, fångstgrupp och fångsttid. Ett dataset som sparades som v<N> flyttas upp till roten vid start, och ett dataset i det tidigare COCO-formatet konverteras automatiskt till YOLO. Klassändringar skriver om label-filernas index så att sparade annoteringar behåller sin klass. export_yolo, export_coco och export_rfdetr skriver träningsklara kataloger med manifest och tömmer katalogen först; yolo-exporten kopierar images/ och labels/ och delar train/val per fångstgrupp, medan rfdetr-exporten delar upp i train/valid/test med _annotations.coco.json per split. Kataloger under ~/.xray-detector.
