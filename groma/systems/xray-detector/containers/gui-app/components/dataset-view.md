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
description: Bläddrar sparade bilder i datumsektioner med ett kort per fångst.
---

Visar datasetet i en sektion per datum bilderna fångades, med datumet som rubrik. Inom sektionen är varje fångst ett kort med fångstens tid, antal bilder och objekt samt bildparet; korten läggs efter varandra på samma rad och radbryts när raden är full. Ett klick markerar hela fångsten, dubbelklick öppnar den i Annotation och Ta bort markerade tar bort alla bilder i den med bekräftelsedialog; knappen visar hur många bilder som är markerade. Fångsterna listas med det nyaste datumet överst; valet Nyast först/Äldst först i vyens inställningar (dataset/sort_order) bygger om listan. Osparade fångster från pending-kön ligger i en egen sektion överst, med rubriken OSPÅRAD, följer samma ordning och kan annoteras klart eller raderas. Knapparna Exportera COCO och Exportera YOLO skriver datasetet till exports/ i en arbetstråd med upptagenindikatorn, och resultatet rapporteras i statusraden.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/ui/busy_indicator.py](../../../../../../xray_detector/ui/busy_indicator.py) | Visar upptagenindikator | Qt-widget |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | Öppnar vyens inställningar | Qt-widget |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/application/dataset_service.py](../../../../../../xray_detector/application/dataset_service.py) | Listar, raderar och exporterar datasetet | direkt anrop |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/application/background_task.py](../../../../../../xray_detector/application/background_task.py) | Läser datasetet och exporterar i bakgrunden | Qt-signaler |
| [xray_detector/ui/dataset_view.py](../../../../../../xray_detector/ui/dataset_view.py) | [xray_detector/dataset/store.py](../../../../../../xray_detector/dataset/store.py) | Listar och raderar bilder | YOLO-txt + cv2.imread |
