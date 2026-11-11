---
type: C4 Component
title: Videotjänst
status: stable
groma:
  id: video-service
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/video_service.py
  group: Video och detektion
description: Bygger videokällor (UVC, fil, ingen) och delegerar till kameratrådarna.
---

Applikationslagrets fasad över CameraService: detektionsvyn anropar set_source(source_id, kind, value, mode) och tjänsten bygger UvcSource eller FileSource internt, så att UI:t inte importerar infrastructure. Mode bär vald upplösning och pixelformat för UVC-källor. Hanterar även set_detector (alla strömmar), stop_source och stopp av alla strömmar vid avstängning.
