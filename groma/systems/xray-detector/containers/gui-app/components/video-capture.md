---
type: C4 Component
title: Videoinspelning
status: stable
groma:
  id: video-capture
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/capture/camera_service.py
    - scanner: python
      file: xray_detector/capture/source.py
    - scanner: python
      file: xray_detector/infrastructure/video/camera_service.py
    - scanner: python
      file: xray_detector/infrastructure/video/source.py
    - scanner: python
      file: xray_detector/infrastructure/video/__init__.py
    - scanner: python
      file: xray_detector/infrastructure/__init__.py
    - scanner: python
      file: xray_detector/infrastructure/video/devices.py
  group: Video och detektion
  technology: OpenCV VideoCapture, QThread
description: Läser två parallella videoströmmar i trådar.
---

CameraService håller en StreamWorker (QThread) per källa ("left"/"right"). Varje worker äger sin egen detektionssmoother, mäter faktisk bildfrekvens över 30 ramar och signalerar när källan tappas. VideoSource-abstraktionen har UvcSource och FileSource. UvcSource öppnar med DSHOW först och MSMF som fallback; vald upplösning och pixelformat måste anges i öppningsanropet eftersom DSHOW ignorerar CAP_PROP_FOURCC efter öppning, och utan valt läge begärs 1920x1080. FileSource spelar upp i videons egen bildfrekvens och börjar om vid filslut. Detektorn injiceras per ström och körs på varje inläst ram.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/capture/camera_service.py](../../../../../../xray_detector/capture/camera_service.py) | [xray_detector/detection/base.py](../../../../../../xray_detector/detection/base.py) | Kör detektor per ram | injicerat anrop |
| [xray_detector/capture/source.py](../../../../../../xray_detector/capture/source.py) | [uvc-kameror](../../../../../externals/uvc-kameror.md) | Fångar ramar | OpenCV VideoCapture (DSHOW) |
