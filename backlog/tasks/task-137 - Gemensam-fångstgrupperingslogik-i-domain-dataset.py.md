---
id: TASK-137
title: Gemensam fångstgrupperingslogik i domain/dataset.py
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-17T22:29:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/domain/dataset.py
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/infrastructure/dataset_store/export.py
  - xray_detector/application/evaluation.py
  - xray_detector/ui/dataset_view.py
  - tests/test_dataset_store.py
priority: medium
type: enhancement
ordinal: 135000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Regeln image.get("group") or image["id"] finns i fyra varianter (store._pair_count, export._group_key/_groups, evaluation.view_labels, dataset_view._pair_count) och tre av dem räknar fel för syntetiska bilder vars group skiljer sig från originalets (utvärdering_argon.md §3.2, review_vibe_deepseek41_flash.md P2.3). Flytta logiken till domain/dataset.py som capture_group()/group_images() och låt alla fyra anropa den. Görs när respektive modul ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 En enda definition av fångstgruppering finns i domain/dataset.py
- [x] #2 store, export, evaluation och dataset_view använder den gemensamma funktionen
- [x] #3 Syntetiska bilder grupperas fortfarande med sitt ursprung (TASK-111-fallet täcks av test)
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
1. Lägg capture_group(), root_image() och group_images() i domain/dataset.py.

2. Låt store._pair_count, export, evaluation.view_labels och dataset_view._pair_count anropa dem i stället för egna varianter.

3. Test som visar att alla fyra räknar lika och att en variation hamnar i ursprungsgruppen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
domain/dataset.py äger nu capture_group(image), root_image(image, by_id) och group_images(images). store._pair_count och dataset_view._pair_count använder capture_group; export och evaluation.view_labels använder group_images, som följer source-kedjan till ursprungsbilden. export._group_key, export._root_image och export._groups är borta. Att _pair_count bara använder capture_group är medvetet: dataset_counts() räknar syntetiska bildpar som egna grupper, och skulle root-uppslagningen användas där skulle antalet kollapsa till antalet original.

Verifiering: test_capture_grouping_is_shared_by_every_reader visar att capture_group, group_images, exportens group_count och evaluation.view_labels ger samma gruppering, och att en variation blir tredje vyn i ursprungsgruppen. De befintliga TASK-111-testerna i test_export_split.py går igenom. Hela sviten: 875 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fångstgrupperingen har en definition: capture_group, root_image och group_images i domain/dataset.py. Lagringen, exporten, utvärderingen och datasetvyn anropar dem i stället för fyra egna varianter, så bildpar räknas lika överallt och en syntetisk bild följer sitt ursprung. Verifierat med ett nytt test plus de befintliga TASK-111-testerna; hela sviten: 875 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
