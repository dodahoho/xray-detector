---
id: TASK-62
title: Annotera - Spara till dataset disabled tills ändringar finns att spara
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T12:54:00Z'
updated_date: '2026-11-12T13:08:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När man öppnar annoteringsvyn genom att klicka på bilder som finns i dataset bör knappen "Spara till dataset" vara disabled tills någon ändring är gjord. I annat fall får man dubbletter i dataset om någon trycker på knappen utan att någon ändring är gjord.

Den ska däremot inte vara disabled när man kommer in från Detektionsvyn och fångad bild.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Spara till dataset är disabled när annoteringen öppnas från Dataset med bilder som redan ligger i datasetet
- [x] #2 Spara till dataset är enabled direkt när annoteringen öppnas från Detektion (Fånga bilder)
- [x] #3 Spara till dataset är enabled direkt när annoteringen öppnas från Dataset med en osparad fångst
- [x] #4 Knappen blir enabled så snart en ändring görs och disabled igen om ändringen kastas
- [x] #5 Tester täcker alla tre vägarna in samt ändring och kastad ändring
- [x] #6 README och groma-arkitekturen beskriver beteendet
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
1. AnnotationView får flaggan _save_requires_change som sätts av load_captures(already_saved=...): bilder som redan ligger i datasetet kräver en ändring, en ny fångst gör det inte.
2. _update_save_button() håller knappen i takt med is_dirty(); canvas.changed, mark_clean() och _on_save_finished() anropar den i stället för att sätta enabled direkt.
3. Huvudfönstret skickar already_saved=True bara när dubbelklicket i datasetvyn gav sparade bilder; en PendingCapture och Fånga bilder lämnas som de är.
4. Ny testfil tests/test_annotation_save_button.py: de tre vägarna in, ändring, kastad ändring.
5. Uppdatera README och groma-beskrivningarna av annoteringsvyn och huvudfönstret.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AnnotationView har fått flaggan _save_requires_change som load_captures(already_saved=...) sätter. _update_save_button() håller Spara till dataset i takt med is_dirty(): canvas.changed, mark_clean() och _on_save_finished() anropar den i stället för att sätta enabled direkt, och load_captures avslutar med mark_clean() så en ny laddning alltid börjar utan osparade ändringar. Huvudfönstret skickar already_saved=True bara när dubbelklicket i datasetvyn gav sparade bilder; en PendingCapture (osparad fångst) och Fånga bilder lämnas enabled. Nya tests/test_annotation_save_button.py täcker de tre vägarna in plus ändring, kastad ändring och nästa fångst; de två beteendetesterna fäller den gamla koden (2 failed) och passerar med ändringen. Hela sviten: 427 passed, 1 skipped. Ruff: inga nya anmärkningar i ändrade filer (tre sedan tidigare i annotation_view.py). README och groma-beskrivningarna av annoteringsvyn och huvudfönstret uppdaterade.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Spara till dataset är nu avstängt när annoteringen öppnas från Dataset med bilder som redan ligger i datasetet, och aktiveras först när en ändring är gjord. En ny fångst från Detektion och en osparad fångst från Dataset kan sparas direkt, eftersom de inte finns i datasetet än. AnnotationView har flaggan _save_requires_change som load_captures(already_saved=...) sätter, och _update_save_button() håller knappen i takt med is_dirty() via canvas.changed, mark_clean() och _on_save_finished(); load_captures avslutar med mark_clean() så en ny laddning alltid börjar utan osparade ändringar. Huvudfönstret skickar already_saved=True bara när dubbelklicket i datasetvyn gav sparade bilder. Verifierat med nya tests/test_annotation_save_button.py (6 tester: de tre vägarna in, ändring via radering, kastad ändring och nästa fångst); de två beteendetesterna fäller den gamla koden (2 failed) och passerar med ändringen. Hela sviten: 427 passed, 1 skipped. Ruff: inga nya anmärkningar i ändrade filer. README och groma-arkitekturen beskriver beteendet. Kvar att göra: ingen känd följdändring.
<!-- SECTION:FINAL_SUMMARY:END -->
