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

Applikationslagrets register: MODEL_SPECS listar YOLO26 nano/small/medium och RF-DETR nano/small/medium/large, spec_by_key/create_detector bygger vald detektorbackend, och device_status() ger text och färg för enhetsindikatorn (CUDA/CPU/torch saknas) som detektionsvyn visar. RF-DETR-posten är avstängd och märkt när rfdetr-paketet saknas. Ligger i applikationslagret eftersom UI:t inte ska importera infrastructure.
