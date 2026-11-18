---
type: C4 Component
title: Model combo
status: stable
groma:
  id: model-combo
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/model_combo.py
description: Modellväljaren som delas av detektions- och träningsvyn.
---

Båda vyerna byggde samma QComboBox ur modellistan och inaktiverade RF-DETR på samma sätt när paketet saknades. Skillnaden var bara vilken text som lades till, så regeln bor här i stället för i två kopior.
