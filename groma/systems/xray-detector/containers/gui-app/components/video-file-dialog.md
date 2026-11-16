---
type: C4 Component
title: Filväljarens katalog
status: stable
groma:
  id: video-file-dialog
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/video_file_dialog.py
description: Kommer ihåg katalogen filväljaren för videofiler öppnas i.
---

Filväljaren för videofiler öppnas i projektets media/, där demovideorna ligger, när ingen katalog är sparad. Väljer användaren en fil någon annanstans sparas filens katalog i QSettings under detection/file_dir, så nästa dialog öppnas där i stället. En sparad katalog som inte längre finns hoppas över, så dialogen aldrig öppnas i en borttagen mapp.
