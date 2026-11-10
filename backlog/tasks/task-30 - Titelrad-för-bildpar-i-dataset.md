---
id: TASK-30
title: Titelrad för bildpar i dataset
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T09:06:00Z'
updated_date: '2026-11-10T09:18:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ersätt "Fångst 1", "Fångst 2" osv med datum och tid när bilderna fångades 

YYYY-MM-DD HH:MM:SS
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Rubriken för en fångst visar datum och tid i formatet YYYY-MM-DD HH:MM:SS
- [x] #2 Tiden är den tidpunkt då bilderna fångades
- [x] #3 Äldre dataset utan sparad tid faller tillbaka på bildfilens tidsstämpel
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
1. add_samples skriver 'captured' (ISO-tid) på varje bild; tiden kommer från pending-fångstens saved_at när den finns, annars now().
2. PendingCapture får saved_at och pending_saved_at() läser indexet utan att dekoda bilder.
3. Datasetvyn visar tiden som 'YYYY-MM-DD HH:MM:SS' i rubriken i stället för 'Fångst N'; äldre dataset faller tillbaka på bildfilens mtime.
4. Tester: rubriken visar tiden, fallback för äldre dataset, pending visar saved_at.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rubriken visar nu fångsttiden i stället för 'Fångst N'. add_samples tar en valfri captured-parameter och skriver 'captured' (ISO) på varje bild i fångsten. AnnotationView._on_save hämtar tiden från pending-indexets saved_at via DatasetService.pending_saved_at(), så tiden är när bilderna fångades (knapptrycket) och inte när annoteringen sparades. PendingCapture får saved_at, och pending_saved_at() läser bara indexet i stället för att dekoda bilderna. Datasetvyn formaterar till lokal 'YYYY-MM-DD HH:MM:SS'; äldre dataset utan fältet faller tillbaka på bildfilens mtime, och osparade fångster visar 'Osparad · <tid>'.

Verifiering: 5 nya tester i tests/test_dataset_header.py (add_samples skriver tiden, rubriken visar den, mtime-fallback för äldre dataset, osparad fångst visar saved_at, samt ett helt flöde fånga -> spara som bevisar att datasetet behåller pending-tiden). Hela sviten 129 passed, 1 skipped. Offscreen: rubriken blir '2026-11-10 09:56:38 · 2 bilder · 2 objekt'.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetvyns rubrik visar nu när bilderna fångades i formatet YYYY-MM-DD HH:MM:SS i stället för 'Fångst 1', 'Fångst 2'. Tiden skrivs som 'captured' på varje bild när fångsten sparas, och hämtas från pending-indexets saved_at som skrevs vid knapptrycket — alltså fångsttiden, inte tiden då annoteringen sparades. Äldre dataset utan fältet faller tillbaka på bildfilens mtime, och osparade fångster visar 'Osparad · <tid>'.

Verifierat: 5 nya tester, inklusive ett helt flöde fånga -> spara som bevisar att datasetet behåller pending-tiden; hela sviten 129 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
