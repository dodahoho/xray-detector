---
type: C4 Component
title: Capture card
status: stable
groma:
  id: capture-card
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/capture_card.py
description: Kort och tumnaglar för en fångst i datasetvyn.
---

CaptureCard fångar klick på hela kortets yta och markerar hela fångsten; klick på rubrik, klassmärken och marginal når hit, medan tumnaglarna har egna klick- och dubbelklickssignaler. Thumbnail visar en bild i paret och byter bara ramfärg när den markeras, så bildens storlek håller sig fast och korten intill inte flyttas. Widgetarna låg tidigare i dataset_view.py.
