---
id: TASK-166
title: Annotering - Zoomfunktion direkt efter klick på knappar + eller -
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-20T11:00:00Z'
updated_date: '2026-11-20T11:31:00Z'
labels: []
dependencies: []
references:
  - annotation-view
  - xray_detector/ui/annotation_view.py
modified_files:
  - xray_detector/ui/annotation_view.py
  - tests/test_annotation_zoom.py
  - docs/beteende.md
type: bug
ordinal: 302000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När jag trycker på knappar för + (zooma in) eller - (zooma ut) så sker inte zoomning i bilden direkt. Jag måste klicka igen någonstans i vyn för att zoomningen ska ske. Det är en bugg och zoomningen i bilden ska såklart ske direkt när man klickat på +/- knapp
<!-- SECTION:DESCRIPTION:END -->

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
1. Reproducera: zoom_at() i AnnotationCanvas ändrar _zoom och _pan men anropar aldrig update(), så bilden ritas inte om förrän något annat (t.ex. ett musklick) begär en ompritning. Verifierat med en räknare på Paint-händelser: efter klick på + ritas bara etikettens yta om, inte bilden.
2. Rätta: anropa self.update() i zoom_at(), så både +/- knapparna och Ctrl+hjul ritar om bilden direkt.
3. Tester i tests/test_annotation_zoom.py: ett Paint-händelsefilter på canvasen ska visa att hela bildytan ritas om direkt efter klick på +, - och 100 %.
4. Uppdatera docs/beteende.md om formuleringen behöver förtydligas.
5. Kör testsviten och ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Orsak: zoom_at() i AnnotationCanvas uppdaterade _zoom, _pan och etiketten men anropade aldrig update(). Canvasen ritas bara om när något begär det, så bilden stod kvar på den gamla nivån tills ett musklick i vyn (mousePressEvent anropar update()) begärde en ompritning. Etiketten uppdaterades däremot direkt, eftersom QLabel ritar om sig själv.

Rättning: self.update() sist i zoom_at(). Både +/- knapparna, 100 %-knappen och Ctrl+hjul går genom zoom_at, så alla tre ritar nu om bilden direkt. reset_view() anropade redan update().

Verifiering: ett Paint-händelsefilter på canvasen visar att hela ytan (0,0,400,300) ritas om direkt efter klick på +, − och 100 %, och efter Ctrl+hjul. Före rättningen rittades bara etikettens yta (44,12,56,32) om. Två nya tester i tests/test_annotation_zoom.py fäller utan rättningen och passerar med den. Hela sviten: 1003 passed, 1 skipped. ruff check: All checks passed.

Dokumentation: docs/beteende.md säger nu att bilden ritas om direkt när nivån ändras.
<!-- SECTION:NOTES:END -->
