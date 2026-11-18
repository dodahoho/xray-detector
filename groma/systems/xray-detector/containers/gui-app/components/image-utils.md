---
type: C4 Component
title: Image utils
status: stable
groma:
  id: image-utils
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/image_utils.py
      symbol: bgr_to_qimage
description: BGR till QImage, delad mellan vyerna.
---

OpenCV arbetar i BGR och Qt ritar RGB. Konverteringen låg tidigare i tre kopior med olika hantering av bufferten; här finns en implementation som alltid lämnar ifrån sig en egen kopia, så bilden inte pekar på en numpy-array som frigörs när funktionen returnerar.
