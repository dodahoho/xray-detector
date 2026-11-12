---
id: TASK-69
title: Annotation - Bort med knapp "Ta bort markerade"
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T17:15:00Z'
updated_date: '2026-11-12T17:22:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 67000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Den knappen behövs inte.
Ta bort enskilda anotationer gör man med tangentbord (delete eller backspace)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Knappen "Ta bort markerad" finns inte längre i annoteringsvyn
- [x] #2 En markerad annotering tas bort med Delete eller Backspace på tangentbordet
- [x] #3 Inga tester eller genvägar refererar till den borttagna knappen
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
1. Ta bort delete_button och _on_delete ur AnnotationView; tangentbordet sköter borttagning i AnnotationCanvas.keyPressEvent.
2. Uppdatera test_shortcuts.py så knappen inte förväntas.
3. Kör annoterings- och genvägstesterna.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Borttagen knapp: delete_button och _on_delete i AnnotationView är borta. Borttagning sker som förut med Delete/Backspace i AnnotationCanvas.keyPressEvent, vilket redan täcktes av test_annotation_canvas.py. Nya tester i test_annotation_ux.py: knappen finns inte och Delete tar bort markerad rektangel i vyn. test_shortcuts.py kontrollerar inte längre knappen. README: genvägstabellen och annoteringsavsnittet uppdaterade.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Annoteringsvyn har ingen "Ta bort markerad"-knapp längre. En markerad rektangel tas bort med Delete eller Backspace, som redan var kopplat i AnnotationCanvas. Verifierat med uv run pytest på test_annotation_ux.py, test_annotation_canvas.py, test_shortcuts.py, test_annotation_classes.py, test_annotation_navigation.py, test_annotation_save_button.py och test_gui_smoke.py (62 tester, alla gröna). README:s genvägstabell och annoteringsavsnitt beskriver tangentbordsborttagningen i stället för knappen.
<!-- SECTION:FINAL_SUMMARY:END -->
