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
description: Visar klass och sannolikhet högst upp i videofönstret, ett märke per detekterad klass.
---

Ger detektionsvyn ett märke per detekterad klass, med klassens namn och sannolikhet på en fast plats i videofönstret och klassens färg som bakgrund, så klassen syns även när rutans etikett drunknar i bilden. Detekteras flera klasser samtidigt staplas märkena uppifrån och ned med den säkraste klassen överst, så alla syns utan att skriva över varandra; fler märken än det finns plats för ritas inte. Varje klass räknar sammanhängande ramar med och utan detektion: märket visas först efter ett inställbart antal ramar med klassen och döljs först efter ett inställbart antal ramar utan, så en detektion nära confidence-tröskeln inte får märket att flimra. Märkena ritas på den skalade bilden, så textstorleken inte beror av källans upplösning.
