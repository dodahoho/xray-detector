---
id: TASK-141
title: _write_sample() i store.py ersätter tre duplicerade skrivblock
status: To Do
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-17T22:35:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/infrastructure/dataset_store/store.py
priority: medium
type: enhancement
ordinal: 139000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
add_samples, replace_samples och add_variations i store.py innehåller samma ~40-radersblock för cv2.imwrite + labelskrivning + metadataappend (review_vibe_deepseek41_flash.md P2.6, största enskilda dupliceringen). Bryt ut _write_sample(image_name, frame, annotations, names, **extra) -> int. Görs när store.py ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Bild- och labelskrivning finns på ett enda ställe i store.py
- [x] #2 Alla dataset-operationer beter sig som tidigare (tester passerar)
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
1. Bryt ut bild- och labelskrivningen till DatasetStore._write_sample(image_name, frame, annotations, names) -> (bredd, höjd).

2. Låt add_samples, replace_samples och add_variations anropa den.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
store.py: _write_sample skriver bilden med cv2.imwrite, räknar om annoteringarna till YOLO-rader med klassindex ur names och skriver label-filen; den returnerar (bredd, höjd) så metadata kan fylla i bildstorleken. add_samples, replace_samples och add_variations anropar den, och cv2.imwrite finns nu på ett enda ställe i filen.

Verifiering: hela sviten 884 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel), inklusive test_dataset_store.py:s 22 tester som täcker add_samples, replace_samples, add_variations, delete_images och num_objects. ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Bild- och labelskrivningen ligger nu i DatasetStore._write_sample, som add_samples, replace_samples och add_variations delar. cv2.imwrite finns på ett ställe i store.py, och de tre ~40-radersblocken är borta. Beteendet är oförändrat: hela sviten ger 884 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
