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
description: Visar två live-strömmar med detektionsoverlay och fångar bildpar.
---

Två StreamPanel med källval (ingen, UVC-enhet eller videofil), valbar upplösning och pixelformat för UVC-källor, och en återanslutningsknapp när källan tappas. Panelens egen rad visar bara strömmens bildfrekvens i fps längst till vänster; källans namn står i källväljaren, så raden håller sig kort. Den övre raden har modellval, confidence-tröskel, enhetsindikator (CUDA/CPU), resursmätare för GPU, VRAM, CPU och RAM, knappen Fånga bilder och en av/på-knapp för detektionen. Av/på-knappen visar vad ett klick gör, kopplar bort detektorn från strömmarna och rensar overlayn men behåller modellen i minnet. Overlayn ritar klassens ruta och etikett i klassens färg, och högst upp i varje panel visas ett klassmärke per detekterad klass med klass och sannolikhet: till höger i vänstra panelen och till vänster i högra, så de två panelernas märken hamnar nära varandra. Flera klasser samtidigt staplas uppifrån och ned med den säkraste överst. Märkenas fördröjning ställs in i vyens inställningar tillsammans med klassfiltret. Fångst skickar senaste ramen från båda panelerna till annoteringsvyn.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/capture/camera_service.py](../../../../../../xray_detector/capture/camera_service.py) | Startar strömmar och visar ramar | Qt-signaler |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/detection/registry.py](../../../../../../xray_detector/detection/registry.py) | Skapar detektor från modellval | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/application/model_registry.py](../../../../../../xray_detector/application/model_registry.py) | Skapar detektor och läser enhetsstatus | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/application/video_service.py](../../../../../../xray_detector/application/video_service.py) | Startar och stoppar strömmar | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/busy_indicator.py](../../../../../../xray_detector/ui/busy_indicator.py) | Visar upptagenindikator | Qt-widget |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/application/background_task.py](../../../../../../xray_detector/application/background_task.py) | Laddar modell i bakgrunden | Qt-signaler |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | Öppnar vyens inställningar | Qt-widget |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/badge.py](../../../../../../xray_detector/ui/badge.py) | Ritar klassmärket högst upp i videofönstret | direkt anrop |
