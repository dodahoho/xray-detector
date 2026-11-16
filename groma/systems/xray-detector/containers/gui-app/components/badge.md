---
type: C4 Component
title: Badge
status: stable
groma:
  id: badge
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/badge.py
description: Visar klass och sannolikhet högst upp i videofönstret.
---

Ger detektionsvyn ett märke med klassens namn och sannolikhet på en fast plats i videofönstret, med klassens färg som bakgrund, så klassen syns även när rutans etikett drunknar i bilden. Varje klass räknar sammanhängande ramar med och utan detektion: märket visas först efter ett inställbart antal ramar med klassen och döljs först efter ett inställbart antal ramar utan, så en detektion nära confidence-tröskeln inte får märket att flimra. Syns flera klasser samtidigt visas den med högst sannolikhet. Märket ritas på den skalade bilden, så textstorleken inte beror av källans upplösning.
