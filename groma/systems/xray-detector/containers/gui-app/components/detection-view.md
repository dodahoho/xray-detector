---
type: C4 Component
title: Detektionsvy
status: stable
groma:
  id: detection-view
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/detection_view.py
  group: Användargränssnitt
description: Visar två live-strömmar med detektionsoveralay och fångar bildpar.
---

Två StreamPanel (Ström 1/2) med källval (ingen, UVC 0/1, videofil), modellval, tröskel och enhetsindikator (CUDA/CPU). Fångar senaste ramen från båda panelerna till Annotation. FPS-pacerad uppspelning av videofiler sker i källorna.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/capture/camera_service.py](../../../../../../xray_detector/capture/camera_service.py) | Startar strömmar och visar ramar | Qt-signaler |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/detection/registry.py](../../../../../../xray_detector/detection/registry.py) | Skapar detektor från modellval | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/application/model_registry.py](../../../../../../xray_detector/application/model_registry.py) | Skapar detektor och läser enhetsstatus | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/application/video_service.py](../../../../../../xray_detector/application/video_service.py) | Startar och stoppar strömmar | direkt anrop |
