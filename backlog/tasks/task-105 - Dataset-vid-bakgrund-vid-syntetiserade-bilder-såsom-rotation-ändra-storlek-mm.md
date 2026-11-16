---
id: TASK-105
title: >-
  Dataset - vid bakgrund vid syntetiserade bilder såsom rotation, ändra storlek
  mm
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-16T20:59:00Z'
updated_date: '2026-11-16T21:01:00Z'
labels: []
dependencies: []
type: bug
ordinal: 103000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om man väljer att utöka dataset med bilder ska t ex roterade eller förminskade bilder inte ge svart bakgrund för nya bakgrundsytan. Använd alltid vit bakgrund så att det matchar befintliga bakgrunden på bilderna.
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
1. Sätt borderValue till vitt i rotate() i augment.py, så ytan utanför den roterade bilden matchar bildernas vita bakgrund (verifierat: median 254, hörn 255 i media-videorna).
2. Uppdatera modulens docstring som i dag säger att ytan blir svart.
3. Anpassa testbilden i test_dataset_variations.py till vit bakgrund med mörkt objekt, så objektet går att hitta även när ramen är vit, och lägg till ett test som låser att ramen är vit.
4. Verifiera med sviten.
<!-- SECTION:PLAN:END -->
