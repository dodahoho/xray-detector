---
id: TASK-72
title: Träning - Inställning av train/validate split
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T19:55:00Z'
updated_date: '2026-11-12T20:21:00Z'
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
- [x] #1 Träningsvyns inställningar har en andel i procent för hur mycket av datasetet som används till train; resten blir validering
- [x] #2 Andelen styr både YOLO- och RF-DETR-exporten och träningsvyns Train/val-redovisning
- [x] #3 Train/val-redovisningen anger antal bildpar i stället för antal enskilda bilder
- [x] #4 Testerna för export, delning och inställningar passerar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. train_ratio(settings) och TrainValSplitSection i settings_dialog.py; nyckeln training/train_ratio med 80 % som default.

2. export_yolo och export_rfdetr tar en ratio och skickar den vidare till train_val_split; DatasetService vidarebefordrar den.

3. group_count i export.py; DatasetService.train_val_counts returnerar antal bildpar.

4. Träningsvyn visar Train/val i par, uppdaterar vid ändrad andel och skickar andelen vid export; datasetvyns YOLO-export använder samma andel.

5. Nya tester för ratio-styrd delning, parräkning och inställningssektionen; README uppdateras.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Andelen sparas som procent i training/train_ratio (default 80) och läses via train_ratio(settings) som 0-1, klämd till 1-99 så både train och val får minst en grupp. TrainValSplitSection ligger i träningsvyns inställningsdialog tillsammans med träningsschemat, och ratio_changed uppdaterar redovisningen medan dialogen är öppen. export_yolo/export_rfdetr tar en ratio som skickas vidare till train_val_split; datasetvyns YOLO-export använder samma andel så de två exporterna inte delar olika. group_count räknar fångstgrupper och DatasetService.train_val_counts returnerar bildpar. Manifestets num_train/num_val är kvar som bildantal eftersom de beskriver de exporterade filerna, inte GUI-redovisningen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Train/val-delningen går att ställa in i träningsvyns inställningar som en andel i procent (training/train_ratio, default 80 %). Andelen styr YOLO- och RF-DETR-exporten samt datasetvyns YOLO-export, och träningsvyns redovisning visar nu antal bildpar ("Train/val: 5/1 par") i stället för enskilda bilder. Verifierat: test_train_ratio_is_read_and_written och test_train_ratio_keeps_a_group_on_each_side (sparning och klämning), test_training_settings_open_the_train_val_split (sektionen i dialogen), test_training_view_shows_train_val_in_pairs (5/1 par default och 3/3 par vid 50 %), test_training_start_exports_with_the_chosen_ratio (andelen når exporten), test_export_yolo_uses_the_ratio och test_export_rfdetr_uses_the_ratio (6/6 bilder vid 50 % av sex par) samt test_split_ratio_controls_the_group_counts. Hela sviten: 493 passed, 1 skipped. README beskriver inställningen och nyckeln.
<!-- SECTION:FINAL_SUMMARY:END -->
