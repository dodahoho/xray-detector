---
type: C4 Component
title: Modellregister
status: stable
groma:
  id: model-registry
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/model_registry.py
  group: Video och detektion
description: Modellspecar, detektorfabrik och enhetsstatus.
---

Applikationslagrets register: MODEL_SPECS listar YOLO26 n/s/m och RF-DETR base, spec_by_key/create_detector bygger vald detektorbackend, och device_status() ger text+färg för enhetsindikatorn (CUDA/CPU/torch saknas) som detektionsvyn visar. Flyttad hit från infrastructure när registry.py blev applikationstjänst.
