---
type: C4 Component
title: Datasetvy
status: stable
groma:
  id: dataset-view
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/dataset_view.py
  group: Användargränssnitt
description: Bläddrar sparade bilder som grupperade thumbnails.
---

Visar en datasetversion som fångstgrupper (bilder som fångats samtidigt ramas in tillsammans), med versionsval, markering, dubbelklick som öppnar gruppen i Annotation och borttagning med bekräftelsedialog.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/dataset/store.py](../../../../../../xray_detector/dataset/store.py) | Listar och raderar bilder | COCO JSON + cv2.imread |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/application/dataset_service.py](../../../../../../xray_detector/application/dataset_service.py) | Listar och raderar bilder | direkt anrop |
