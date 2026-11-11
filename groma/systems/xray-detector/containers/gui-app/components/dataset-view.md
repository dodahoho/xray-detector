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

Visar datasetet som fångstgrupper (bilder som fångats samtidigt ramas in tillsammans), med markering av hela gruppen, dubbelklick som öppnar gruppen i Annotation och borttagning med bekräftelsedialog. Varje grupprubrik visar när fångsten gjordes samt antal bilder och objekt, och knappen Ta bort markerade visar hur många bilder som är markerade. Fångsterna listas med den nyaste överst; valet Nyast först/Äldst först i vyens inställningar (dataset/sort_order) bygger om listan. Osparade fångster från pending-kön listas först, med rubriken OSPÅRAD, följer samma ordning och kan annoteras klart eller raderas. Knapparna Exportera COCO och Exportera YOLO skriver datasetet till exports/ i en arbetstråd med upptagenindikatorn, och resultatet rapporteras i statusraden.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/dataset/store.py](../../../../../../xray_detector/dataset/store.py) | Listar och raderar bilder | COCO JSON + cv2.imread |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/ui/busy_indicator.py](../../../../../../xray_detector/ui/busy_indicator.py) | Visar upptagenindikator | Qt-widget |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | Öppnar vyens inställningar | Qt-widget |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/application/dataset_service.py](../../../../../../xray_detector/application/dataset_service.py) | Listar, raderar och exporterar datasetet | direkt anrop |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/application/background_task.py](../../../../../../xray_detector/application/background_task.py) | Läser datasetet och exporterar i bakgrunden | Qt-signaler |
