---
type: C4 Component
title: Style
status: stable
groma:
  id: style
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/style.py
description: Gemensamma mått och knappfabrik som håller GUI-elementen likadana i alla vyer.
---

Alla knappar har samma höjd (BUTTON_HEIGHT) och klassknapparna samma bredd (ICON_BUTTON_WIDTH). Vyerna skapar knappar med button() i stället för QPushButton, så en ändring av måtten slår igenom överallt. primary=True markerar vyens huvudåtgärd med fet stil i stället för en högre knapp, och apply_metrics() ger samma mått åt widgetar som Qt har skapat, som dialogens standardknappar. height=None lämnar måttet till Qt när ett element behöver egna inställningar.
