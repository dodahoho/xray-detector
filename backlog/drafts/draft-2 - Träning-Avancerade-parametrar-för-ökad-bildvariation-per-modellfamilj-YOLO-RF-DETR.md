---
id: DRAFT-2
title: >-
  Träning - Avancerade parametrar för ökad bildvariation per modellfamilj
  (YOLO/RF-DETR)
status: To Do
assignee: []
created_date: '2026-11-19T09:27:00Z'
labels: []
dependencies: []
ordinal: 299000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
RF-DETR och YOLO har en del avancerade träningsparametrar som inte är direkt kompatibla, tex när det kommer till automatisk augmentation av bilder i träningsdata.

RF-DETR har t ex scale_jitter och 

YOLO verkar kunna använda följande som parametrar till train() för att styra automatisk augmentation (öka bildvariationen syntetiskt):

    # Geometrisk augmentation
    mosaic=0.0,
    scale=0.0,
    translate=0.0,
    degrees=0.0,
    shear=0.0,
    perspective=0.0,

    # Spegling
    fliplr=0.5,
    flipud=0.5,

    # Bevara materialfärgerna
    hsv_h=0.0,
    hsv_s=0.0,
    hsv_v=0.0,

    # Ingen bildblandning
    mixup=0.0,
    cutmix=0.0,
    copy_paste=0.0,
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
