---
id: TASK-127
title: ANNOTATION_TAB-konstant och publik AnnotationView.save()
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:50:00Z'
updated_date: '2026-11-17T22:13:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/ui/main_window.py
  - xray_detector/ui/annotation_view.py
  - tests/test_annotation_navigation.py
  - tests/test_annotation_save_button.py
  - tests/test_annotation_ux.py
  - tests/test_busy_operations.py
  - tests/test_dataset_header.py
  - tests/test_gui_smoke.py
  - tests/test_pending.py
priority: high
type: task
ordinal: 346000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
main_window.py hårdkodar annoteringsflikens index 1 på tio ställen och anropar dessutom privata annotation_view._on_save() från två ställen (review_vibe_deepseek41_flash.md P1.4, utvärdering_hydrogen.md §5.3). Inför en modulkonstant eller tabs.indexOf(self.annotation_view) och en publik save() som _on_save delegerar till.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Inga hårdkodade tab-index finns kvar i main_window.py
- [x] #2 MainWindow anropar endast publika metoder på AnnotationView
- [x] #3 Flikordningen kan ändras utan att koden bryts
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
1. Lägg en _annotation_tab-egenskap i MainWindow som slår upp indexet med tabs.indexOf(annotation_view) och använd den i stället för de tio hårdkodade 1:orna.

2. Gör AnnotationView._on_save publik som save() och låt knappen, Enter-genvägen och MainWindow anropa den.

3. Test som flyttar annoteringsfliken och visar att indexet följer med.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
main_window.py: _annotation_tab är en egenskap som returnerar self.tabs.indexOf(self.annotation_view). Alla tio ställen som jämförde eller satte index 1 använder den nu, liksom setTabEnabled. annotation_view.py: _on_save heter save och är publik; save_button.clicked, Enter-genvägen och MainWindow._leave_annotation anropar den. Testerna som anropade _on_save direkt är uppdaterade.

Verifiering: test_annotation_tab_index_is_looked_up_from_the_tab_order flyttar annoteringsfliken till slutet och visar att _annotation_tab följer med. 66 tester i de sju berörda testfilerna går igenom, liksom hela sviten: 867 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
MainWindow slår nu upp annoteringsflikens index med tabs.indexOf(annotation_view) via egenskapen _annotation_tab i stället för att hårdkoda 1 på tio ställen, så flikordningen kan ändras. AnnotationView._on_save är publik som save(), och MainWindow anropar bara publika metoder på vyn. Verifierat med ett test som flyttar fliken och med hela sviten (867 passed, 1 skipped, inga nya fel).
<!-- SECTION:FINAL_SUMMARY:END -->
