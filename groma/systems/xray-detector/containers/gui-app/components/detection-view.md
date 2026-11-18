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

Två StreamPanel med egen källväljare (UVC-enhet eller videofil), upplösning och pixelformat, plus en rad med modellväljare, konfidenströskel, enhetslabel, resursmätare för CPU, RAM och VRAM samt av/på-knapp för detektionen. Panelerna ritar detektionsoverlayn med klassfärg och klassmärken. Modellen laddas i en bakgrundsuppgift och enhetskontrollen körs separat eftersom CUDA-initieringen tar cirka en sekund. Fånga skickar bildparet vidare till annoteringsvyn via MainWindow, och träningsstarten pausar strömmarna. Panelerna, resursmätaren och overlayritningen ligger i ui/stream_panel.py, som vyn importerar.

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
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/video_file_dialog.py](../../../../../../xray_detector/ui/video_file_dialog.py) | Öppnar filväljaren | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/infrastructure/video/camera_service.py](../../../../../../xray_detector/infrastructure/video/camera_service.py) | Startar och stoppar strömmar | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/infrastructure/detectors/base.py](../../../../../../xray_detector/infrastructure/detectors/base.py) | Använder detektorgränssnittet | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/infrastructure/system/resources.py](../../../../../../xray_detector/infrastructure/system/resources.py) | Visar CPU- och VRAM-mätare | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/infrastructure/video/devices.py](../../../../../../xray_detector/infrastructure/video/devices.py) | Listar enhetens lägen | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/infrastructure/video/source.py](../../../../../../xray_detector/infrastructure/video/source.py) | Bygger videokällan | direkt anrop |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/stream_panel.py](../../../../../../xray_detector/ui/stream_panel.py) | Bygger de två videopanelerna | Qt-widget |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/model_combo.py](../../../../../../xray_detector/ui/model_combo.py) | Visar modellväljaren | Qt-widget |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/theme_toggle.py](../../../../../../xray_detector/ui/theme_toggle.py) | Visar temaväxlaren | Qt-widget |
| [xray_detector/ui/detection_view.py](../../../../../../xray_detector/ui/detection_view.py) | [xray_detector/ui/model_settings.py](../../../../../../xray_detector/ui/model_settings.py) | Öppnar modelldialogen | Qt-dialog |
