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

Applikationslagrets fasad över CameraService: detektionsvyn anropar set_source(source_id, kind, value) och tjänsten bygger UvcSource/FileSource internt, så att UI:t inte importerar infrastructure. Hanterar även set_detector (alla strömmar) och stopp av strömmar vid avstängning.
