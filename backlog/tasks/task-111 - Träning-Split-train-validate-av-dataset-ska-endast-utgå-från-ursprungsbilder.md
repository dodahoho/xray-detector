---
id: TASK-111
title: Träning - Split train/validate av dataset ska endast utgå från ursprungsbilder
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T08:31:00Z'
updated_date: '2026-11-17T09:07:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 189000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När ett dataset har utökats med syntetiska bilder är det viktigt att dataset split bara utgår från bildpar som är ursprungsbilder (ej syntetiskt utökade) och att varje syntetiskt utökad bild följer med dess ursprungsbild och alltid hamnar i samma split som ursprunget.

För att man ska kunna lita på validation-fasen av träningen måste det vara ett vattentätt skott mellan train och validation split

En syntetisk bild bör alltså hålla reda vilken bild som är dess ursprung och alltid sorteras i samma training split
<!-- SECTION:DESCRIPTION:END -->

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
1. export.py: _groups() grupperar på ursprungsbildens fångstgrupp, så en syntetisk bild alltid hamnar i samma del som sitt ursprung.
2. _signature() räknar klassuppsättningen på ursprungsbilderna, så stratifieringen bara ser dem.
3. group_count() räknar rotgrupper, så Train/val-siffran i träningsvyn också bara räknar ursprungspar.
4. Tester: syntetiska följer ursprunget över flera seeds, och att delningen är oförändrad när datasetet utökas.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Delningen grupperar nu på ursprungsbildens fångstgrupp: _root_image() följer source-kedjan från en syntetisk bild till originalet, och _groups() använder den gruppen. En variation har eget group-id i datasetet, så utan detta kunde den hamna i en annan del än sitt ursprung.

_signature() räknar klassuppsättningen på ursprungsbilderna, eftersom en variation kan tappa en annotering som hamnat utanför bilden. group_count() räknar rotgrupper, så Train/val-siffran i Dataset-kortet och image_pair_count() i startloggen också bara räknar ursprungspar.

Verifierat: 4 nya tester i tests/test_export_split.py. Tre av dem faller utan fixen (kontrollerat genom att stash:a export.py). Hela sviten: 812 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Train/val-delningen utgår nu bara från ursprungsbildparen. En syntetisk bild följer sitt ursprung via source-kedjan och hamnar därför alltid i samma del som originalet, så en utökning av datasetet aldrig kan läcka mellan train och val. Stratifieringen räknar klassuppsättningen på ursprungsbilderna, och både Train/val-siffran i Dataset-kortet och startloggens bildparsräkning räknar rotgrupper.

Verifierat med fyra nya tester i tests/test_export_split.py: syntetiska följer sitt ursprung över fem seeds, group_count räknar bara ursprungspar, delningen är oförändrad när datasetet utökas, och en variation vars ursprung saknas behåller sin egen grupp. Tre av dem faller utan fixen. Hela sviten: 812 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
