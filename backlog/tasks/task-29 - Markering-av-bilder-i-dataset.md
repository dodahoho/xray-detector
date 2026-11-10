---
id: TASK-29
title: Markering av bilder i dataset
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T09:04:00Z'
updated_date: '2026-11-10T09:14:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Istället för att lägga till en rad "Markerad" på varje bild kan rubrikraden för bildparen bli ifylld vid markering och även lägga in texten Markerad sist i rubrikraden för bildparet
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ingen Markerad-rad visas på varje bild
- [x] #2 Rubrikraden för fångsten fylls med accentfärg vid markering
- [x] #3 Rubrikraden avslutas med Markerad när fångsten är markerad
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
1. Ta bort MARKERAD-badgen från Thumbnail.
2. Spara rubrik och ram per fångst i DatasetView (_group_headers).
3. Vid markering: fyll rubrikraden med accentfärg och avsluta texten med ' · Markerad'; återställ vid avmarkering.
4. Tester: ingen badge, rubriken får texten och stilen, återställs vid avmarkering.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
MARKERAD-badgen på varje bild är borta. DatasetView sparar nu rubrik och ram per fångst i _group_headers (både sparade och osparade), och _update_group_header fyller rubrikraden med accentfärg (#4da3ff, mörk text), avslutar texten med ' · Markerad' och ger ramen 2 px accentfärg. Vid avmarkering återställs rubrikens och ramens ursprungliga stil (grå för sparade, orange streckad för osparade). _group_thumbs ersattes av _thumbs_for_group som slår upp på group_id och därmed fungerar för båda typerna.

Verifiering: 3 nya/uppdaterade tester (ingen MARKERAD-rad på thumbnails, rubriken får texten och stilen, återställs vid avmarkering). Hela sviten 124 passed, 1 skipped. Offscreen-rendering: 0 accentfärgade pixlar före markering och 25120 efter, rubriken går från 'Fångst 1 · 2 bilder · 2 objekt' till '... · Markerad'. DoD #4: README beskriver redan att ett klick markerar hela fångsten; ingen ytterligare användardokumentation behövs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Markeringen av en fångst sitter nu i rubrikraden i stället för som en MARKERAD-rad på varje bild: rubriken fylls med accentfärg, avslutas med ' · Markerad' och ramen runt fångsten får samma accentfärg. Både sparade och osparade fångster återställer sin ursprungliga stil vid avmarkering.

Verifierat: 3 nya/uppdaterade tester; hela sviten 124 passed, 1 skipped. Offscreen-rendering visar 0 accentfärgade pixlar före markering och 25120 efter.
<!-- SECTION:FINAL_SUMMARY:END -->
