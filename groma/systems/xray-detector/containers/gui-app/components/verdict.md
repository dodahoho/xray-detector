---
type: C4 Component
title: Verdict
status: stable
groma:
  id: verdict
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/training/verdict.py
description: Dom över hur en träning slutade.
---

Historikvyn visar mAP, epoker och status, men inte om kurvan planade ut, om modellen övertränade eller om träningen helt enkelt var för kort. Domen räknas fram ur körningens sparade epokvärden, så den går att få fram även för en körning som gjordes innan funktionen fanns.
