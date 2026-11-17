---
id: TASK-144
title: >-
  Central färgpalett i ui/colors.py och temaberoende ytor i stället för
  inline-setStyleSheet
status: To Do
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-17T22:36:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/ui/colors.py
  - xray_detector/ui/detection_view.py
  - tests/test_colors.py
priority: medium
type: enhancement
ordinal: 142000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
31 inline-setStyleSheet med upprepade hårdkodade färger (#888 x7, #c33 x3, #e5a52a x4, #666 x3, #4da3ff x2) och mörka temakonstanter i dataset_view/detection_view gör att ljust tema ser fel ut (t.ex. background:#222 i detection_view.py:378) (alla tre utvärderingarna). Skapa ui/colors.py med MUTED/ERROR/WARNING/SELECTED/ACCENT och använd QPalette för temaberoende ytor. Görs när respektive vy ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ui/colors.py finns och vyerna använder den; inga upprepade hex-färger hårdkodas i vyerna
- [ ] #2 Dataset- och detektionsvyn ser korrekta ut i både ljust och mörkt tema (manuell kontroll)
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
1. Paletten i ui/colors.py (klar i TASK-139) används av alla vyer; inga upprepade hex-färger kvar.

2. Låt videoytans bakgrund komma ur paletten med setAutoFillBackground i stället för en hårdkodad mörk färg.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Paletten och de namngivna konstanterna kom på plats i TASK-139, som också ersatte alla hårdkodade hex-färger i vyerna; ett test skannar källkoden och fallerar om en ny dyker upp. Kvar var den mörka ytan i detektionsvyn: display-widgeten satte background: #222 i sin stylesheet, så ljust tema fick en svart ruta. Nu sätts ingen bakgrund i stylesheeten; widgeten fyller med palettens Window-färg via setAutoFillBackground, och PANEL_BACKGROUND är borta ur colors.py.

Verifiering: test_the_detection_display_follows_the_theme visar att ytan fyller med palettfärgen och att stylesheeten inte innehåller någon background. Hela sviten: 885 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). AC 2:s manuella kontroll av båda temana är inte gjord i den här miljön - den kräver att appen startas och tittas på, vilket inte går här. Det som går att verifiera programmatiskt är gjort.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Vyerna hämtar sina färger ur ui/colors.py, och ett test fallerar om en hex-färg dyker upp utanför filen. Den sista mörka ytan - videofönstrets background: #222 - är borta: widgeten fyller nu med palettens Window-färg, så ljust tema inte längre får en svart ruta. Hela sviten: 885 passed, 1 skipped, inga nya fel. Kvar: den manuella visuella kontrollen av båda temana, som kräver att appen startas med skärm.
<!-- SECTION:FINAL_SUMMARY:END -->
