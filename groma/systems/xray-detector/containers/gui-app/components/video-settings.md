---
type: C4 Component
title: Videoval
status: stable
groma:
  id: video-settings
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/video_settings.py
description: Läser och skriver vald UVC-modalitet i QSettings.
---

Delas av inställningsvyn som skriver valet och detektionsvyn som läser det när en UVC-källa öppnas. Nycklarna video/width, video/height och video/fourcc finns bara här, så de två vyerna inte kan glida isär. Saknat värde betyder att drivrutinen väljer upplösning och format själv.
