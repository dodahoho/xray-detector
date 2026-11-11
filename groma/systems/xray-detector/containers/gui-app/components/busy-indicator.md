---
type: C4 Component
title: Busy indicator
status: stable
groma:
  id: busy-indicator
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/busy_indicator.py
description: Animerad upptagenindikator som läggs över en vy medan ett arbete pågår.
---

Ett halvtransparent överlägg med snurra och text, skapat som barn till den widget det täcker. Samma komponent används av detektions-, dataset-, tränings- och annoteringsvyn. Indikatorn tänds först efter en kort fördröjning, så en operation som hinner klart ändå inte ger en blinkning, och snurran drivs av en timer i GUI-tråden. Det senare är skälet till att arbetet som visas måste ligga utanför GUI-tråden: annars står snurran still.
