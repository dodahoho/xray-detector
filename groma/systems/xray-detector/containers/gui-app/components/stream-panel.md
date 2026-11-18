---
type: C4 Component
title: Stream panel
status: stable
groma:
  id: stream-panel
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/stream_panel.py
description: Videopanel med källväljare, overlay och återanslutning, plus resursmätaren.
---

StreamPanel äger en videoström: källväljare för UVC-enhet eller videofil, upplösning och pixelformat, bildrutan med detektionsoverlay och klassmärken, och återanslutningen när källan tappas. ResourceMeter visar en resurs som etikett, stapel och värde, och draw_detections ritar ruta och etikett för varje detektion. Panelerna låg tidigare i detection_view.py.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/stream_panel.py](../../../../../../xray_detector/ui/stream_panel.py) | [xray_detector/ui/image_utils.py](../../../../../../xray_detector/ui/image_utils.py) | Konverterar ramarna från BGR till QImage | cv2 + QImage |
