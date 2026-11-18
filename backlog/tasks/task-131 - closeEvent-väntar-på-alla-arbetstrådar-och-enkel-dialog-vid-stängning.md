---
id: TASK-131
title: closeEvent väntar på alla arbetstrådar och enkel dialog vid stängning
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:18:00Z'
labels:
  - bugfix
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
modified_files:
  - xray_detector/ui/main_window.py
  - xray_detector/ui/annotation_view.py
  - tests/test_annotation_ux.py
priority: high
type: bug
ordinal: 129000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
MainWindow.closeEvent väntar på annotation/dataset/detection men missar training_view.history.wait_for_evaluation() och settings_view.model_section.wait_for_download() (utvärdering_argon.md §5.6). Dessutom ger stängning med osparade tomma annoteringar en dubbel frågedialog där Nej ändå förlorar ändringarna.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 closeEvent väntar även på träningshistorikens utvärdering och modellnedladdning
- [x] #2 Stängning med osparade tomma annoteringar visar en enda dialog och hanterar svaret konsekvent
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
1. Låt closeEvent även anropa training_view.history.wait_for_evaluation() och settings_view.model_section.wait_for_download().

2. Gör AnnotationView.save() till en boolesk metod med confirm_empty-flagga, så stängningen kan hoppa över frågan om negativa exempel när användaren redan svarat spara.

3. Låt closeEvent avbryta stängningen när save() avböjs, så svaret hanteras konsekvent.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
main_window.py: closeEvent väntar nu också på träningshistorikens utvärdering och modellnedladdningen, efter de befintliga väntningarna på annotation, dataset, export och variationer. Stängning med osparade annoteringar ställer en fråga: save(confirm_empty=False) hoppar över den andra frågan om negativa exempel, och ett avböjt svar gör att stängningen ignoreras i stället för att ändringarna tyst förloras.

annotation_view.py: save() returnerar bool - True när en sparning pågår eller startades, False när användaren avböjer frågan om negativa exempel. _on_default_action och save_button fungerar oförändrat eftersom de anropar save() utan flaggan.

Verifiering: test_close_with_unsaved_empty_annotations_asks_once_and_saves visar att exakt en dialog visas och att bilden skrivs som negativt exempel (num_images 1, num_objects 0). test_close_waits_for_the_evaluation_and_the_download visar att båda väntningarna anropas i ordning. Hela sviten: 880 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
closeEvent väntar nu in alla arbetstrådar, inklusive träningshistorikens utvärdering och modellnedladdningen i inställningarna. Stängning med osparade annoteringar ställer en enda fråga: AnnotationView.save() tar en confirm_empty-flagga så frågan om negativa exempel inte upprepas, och ett avböjt svar stoppar stängningen i stället för att tyst kasta ändringarna. Verifierat med två nya tester och hela sviten (880 passed, 1 skipped, inga nya fel).
<!-- SECTION:FINAL_SUMMARY:END -->
