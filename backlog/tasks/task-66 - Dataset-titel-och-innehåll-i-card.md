---
id: TASK-66
title: Dataset - titel och innehåll i card
status: In Progress
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:28:00Z'
updated_date: '2026-11-12T14:37:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Titeln ska bara ha tid samt en uppräkning av alla objektklasser som bilderna innehåller (utan antal). Uppräkningen av objektklasser görs med badges efter varandra.

Den uppräkning som nu finns under respektive thumbnail i ett card kan tas bort. Endast titelrad och thumbnails i ett card
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Titelraden visar fångstens tid
- [ ] #2 Titelraden visar en badge per objektklass i fångsten, utan antal
- [ ] #3 Ingen uppräkning av klasser under respektive thumbnail i kortet
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
1. Gör rubrikraden till en rad med tidsetikett och en badge per objektklass, färgad med klassens färg.
2. Låt rubrikraden bära färg och bakgrund så markeringen täcker både tid och märken, och behåll breddreservationen för ' · Markerad'.
3. Ta bort bildtexten under thumbnails; osparade fångsters käll-etikett flyttas till en tooltip.
4. Test: titelraden visar tid och en badge per klass utan antal, och inga bildtexter finns kvar i kortet.
<!-- SECTION:PLAN:END -->
