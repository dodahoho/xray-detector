---
id: TASK-29
title: Markering av bilder i dataset
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T09:04:00Z'
updated_date: '2026-11-10T09:12:00Z'
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
- [ ] #1 Ingen Markerad-rad visas på varje bild
- [ ] #2 Rubrikraden för fångsten fylls med accentfärg vid markering
- [ ] #3 Rubrikraden avslutas med Markerad när fångsten är markerad
<!-- AC:END -->

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
1. Ta bort MARKERAD-badgen från Thumbnail.
2. Spara rubrik och ram per fångst i DatasetView (_group_headers).
3. Vid markering: fyll rubrikraden med accentfärg och avsluta texten med ' · Markerad'; återställ vid avmarkering.
4. Tester: ingen badge, rubriken får texten och stilen, återställs vid avmarkering.
<!-- SECTION:PLAN:END -->
