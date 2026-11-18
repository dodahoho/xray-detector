---
type: C4 Component
title: Variation dialog
status: stable
groma:
  id: variation-dialog
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/variation_dialog.py
description: Dialog för att utöka datasetet med syntetiska bildvariationer.
---

Kombinationsläget ställs först, sedan vilka variationstyper som ska användas och hur mycket de får ändra. En typ är avstängd tills dess kryssruta är satt, och då är även typens fält avstängda. Antalet variationer per bildpar gäller bara när en bild får flera typer. Dialogen räknar ut hur många bildpar utökningen ger innan den genomförs.
