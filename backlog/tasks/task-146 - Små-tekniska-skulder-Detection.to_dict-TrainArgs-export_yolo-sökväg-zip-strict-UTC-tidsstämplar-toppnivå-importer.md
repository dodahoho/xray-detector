---
id: TASK-146
title: >-
  Små tekniska skulder: Detection.to_dict, TrainArgs, export_yolo-sökväg, zip
  strict, UTC-tidsstämplar, toppnivå-importer
status: In Progress
assignee: []
created_date: '2026-11-17T20:53:00Z'
updated_date: '2026-11-18T07:39:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
priority: medium
type: enhancement
ordinal: 4000
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Lägg to_dict/from_dict på domain.Detection och låt pending.py använda dem.
2. Sätt strict=True där längderna måste matcha (metrics.recall_at, metrics._class_ap); behåll strict=False där rader får vara kortare (epoch_metrics) eller listorna kan skilja (annotation_view).
3. Byt pending.saved_at och training_view:s körningstid till datetime.now(UTC); nattfönstret i training_service är lokal tid och lämnas.
4. Aktivera PLC0415 i ruff, flytta obefogade lokala importer till toppnivå och märk de medvetet lata (torch, ultralytics, rfdetr, pygrabber, ctypes.wintypes) med noqa. Testerna undantas via per-file-ignores.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Genomfört: Detection.to_dict/from_dict i domain/detection.py; pending.py använder dem. zip strict=True i metrics.recall_at och metrics._class_ap; strict=False kvar i epoch_metrics (Lightning skriver rader kortare än headern, se test_rfdetr_row_without_values) och annotation_view (fler canvases än captures). pending.saved_at och training_view:s now() använder datetime.now(UTC); nattfönstret i training_service jämför lokal tid och lämnas medvetet. PLC0415 är aktiverad i ruff med per-file-ignores för tests/**, och de lata importen är märkta med noqa. Kvar från beskrivningen (utanför AC): TrainArgs-dataclass i train_task.main och att låta export_yolo returnera data.yaml-sökvägen.
<!-- SECTION:NOTES:END -->
