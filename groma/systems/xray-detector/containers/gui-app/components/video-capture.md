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
      file: xray_detector/capture/__init__.py
  group: Video och detektion
  technology: OpenCV VideoCapture, QThread
description: Läser två parallella videoströmmar i trådar.
---

CameraService håller en StreamWorker (QThread) per källa ("left"/"right"). VideoSource-abstraktionen har UvcSource (DSHOW först med MSMF-fallback, 1920x1080) och FileSource (FPS-pacerad uppspelning, loop vid filslut). Detektorn injiceras per ström och körs på varje inläst ram.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/capture/camera_service.py](../../../../../../xray_detector/capture/camera_service.py) | [xray_detector/detection/base.py](../../../../../../xray_detector/detection/base.py) | Kör detektor per ram | injicerat anrop |
| [xray_detector/capture/source.py](../../../../../../xray_detector/capture/source.py) | [uvc-kameror](../../../../../externals/uvc-kameror.md) | Fångar ramar | OpenCV VideoCapture (DSHOW) |
