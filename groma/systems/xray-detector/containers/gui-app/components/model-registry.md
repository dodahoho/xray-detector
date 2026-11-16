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
description: Modellkatalogen, detektorfabriken och enhetsstatus.
---

Applikationslagrets register: ModelCatalog äger modellistan i models/models.json och skriver den när användaren lägger till, byter namn på eller tar bort en modell; MODEL_SPECS är standardlistan som används när filen saknas eller är trasig, medan en tom lista är ett giltigt val. Vikterna anges relativt models_dir, så listan följer med när katalogen pekas om i config.yaml, och familjen avgörs av filändelsen (.pt -> yolo, .pth -> rfdetr). spec_by_key/create_detector bygger vald detektorbackend, och device_status() ger text och färg för enhetsindikatorn (CUDA/CPU/torch saknas) som detektionsvyn visar. RF-DETR-posten är avstängd och märkt när rfdetr-paketet saknas. Ligger i applikationslagret eftersom UI:t inte ska importera infrastructure.
