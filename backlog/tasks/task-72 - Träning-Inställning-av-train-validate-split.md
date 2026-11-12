---
id: TASK-72
title: Träning - Inställning av train/validate split
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-12T19:55:00Z'
updated_date: '2026-11-12T20:16:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/infrastructure/dataset_store/export.py
  - xray_detector/application/dataset_service.py
  - xray_detector/ui/settings_dialog.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/dataset_view.py
  - tests/test_export_split.py
  - tests/test_settings_dialog.py
  - tests/test_busy_operations.py
  - README.md
type: enhancement
ordinal: 70000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Man ska kunna ändra hur stor andel av dataset som används till train respektive validate. Eventuella absoluta siffror ska referera till antal bildpar istället för antal enskilda bilder.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Träningsvyns inställningar har en andel i procent för hur mycket av datasetet som används till train; resten blir validering
- [ ] #2 Andelen styr både YOLO- och RF-DETR-exporten och träningsvyns Train/val-redovisning
- [ ] #3 Train/val-redovisningen anger antal bildpar i stället för antal enskilda bilder
- [ ] #4 Testerna för export, delning och inställningar passerar
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
1. train_ratio(settings) och TrainValSplitSection i settings_dialog.py; nyckeln training/train_ratio med 80 % som default.

2. export_yolo och export_rfdetr tar en ratio och skickar den vidare till train_val_split; DatasetService vidarebefordrar den.

3. group_count i export.py; DatasetService.train_val_counts returnerar antal bildpar.

4. Träningsvyn visar Train/val i par, uppdaterar vid ändrad andel och skickar andelen vid export; datasetvyns YOLO-export använder samma andel.

5. Nya tester för ratio-styrd delning, parräkning och inställningssektionen; README uppdateras.
<!-- SECTION:PLAN:END -->
