---
id: TASK-146
title: >-
  Små tekniska skulder: Detection.to_dict, TrainArgs, export_yolo-sökväg, zip
  strict, UTC-tidsstämplar, toppnivå-importer
status: To Do
assignee: []
created_date: '2026-11-17T20:53:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
priority: medium
type: enhancement
ordinal: 144000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Från review_vibe_deepseek41_flash.md: pending.py handskriver Detection<->dict (flytta to_dict/from_dict till domain/detection.py); train_task.main muterar argparse.Namespace (inför TrainArgs-dataclass); training_view hårdkodar exportlayouten (låt export_yolo returnera data.yaml-sökvägen); zip() utan strict på fyra ställen (store.py:312, smoothing.py:64, metrics.py:153, annotation_view.py:654); blandade tidsformat utan tidszon (datetime.now(UTC) överallt utom nattfönstret); obefogade funktionslokala importer ska till toppnivå (behåll lazy torch/ultralytics/rfdetr med noqa). Görs när respektive modul ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Detection har to_dict/from_dict i domain och pending.py använder dem
- [ ] #2 zip(..., strict=...) används där längderna ska matcha
- [ ] #3 Alla sparade tidsstämplar använder UTC
- [ ] #4 Inga obefogade PLC0415 kvar enligt ruff
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
