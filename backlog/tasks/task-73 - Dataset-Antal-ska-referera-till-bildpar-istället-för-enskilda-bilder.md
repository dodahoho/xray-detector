---
id: TASK-73
title: Dataset - Antal ska referera till bildpar istället för enskilda bilder
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T19:57:00Z'
updated_date: '2026-11-12T20:12:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/dataset_view.py
  - tests/test_dataset_card_click.py
  - tests/test_dataset_selection.py
  - README.md
type: bug
ordinal: 71000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu när man markerar bildpar i dataset och t ex klickar ta bort så räknas antal bilder, men eftersom de alltid hanteras i par så är det så är det alltid bildpar som ska räknas istället för antal enskilda bilder
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Knappen "Ta bort markerade" visar antal markerade bildpar i stället för antal enskilda bilder
- [x] #2 Bekräftelsedialogen och statusraden anger antal bildpar
- [x] #3 Testerna för datasetvyns markering och borttagning passerar
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
1. Räkna markerade fångstgrupper i stället för markerade thumbnails i DatasetView._update_delete_button.

2. Räkna grupper i _on_delete och använd ordet bildpar i dialog och statusrad.

3. Uppdatera test_dataset_selection.py och test_dataset_card_click.py till parräkning.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Datasetvyn räknar nu fångstgrupper (bildpar) i stället för enskilda bilder: _selected_groups() ger antalet markerade par, knappen visar det, och _on_delete använder samma antal i dialog och statusrad. Nya test: test_delete_counts_image_pairs; befintliga markeringstester uppdaterade till (1). 17 tester i test_dataset_selection.py och test_dataset_card_click.py passerar.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetvyn räknar bildpar i stället för enskilda bilder. _selected_groups() returnerar fångstgrupperna som har minst en markerad bild, och både knapptexten ("Ta bort markerade (N)"), bekräftelsedialogen och statusraden använder det antalet. Dialogrutan heter nu "Ta bort bildpar" och texten säger "N bildpar" i stället för "N bild(er)". Verifierat: nytt test test_delete_counts_image_pairs kontrollerar dialogtext och statusrad, markeringstesterna i test_dataset_selection.py och test_dataset_card_click.py förväntar (1) för ett markerat par, och hela sviten ger 485 passed, 1 skipped. README är uppdaterad. Groma-beskrivningen av dataset-view nämner fortfarande antal bilder och behöver cureras separat.
<!-- SECTION:FINAL_SUMMARY:END -->
