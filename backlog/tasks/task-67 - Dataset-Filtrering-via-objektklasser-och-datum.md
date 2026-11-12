---
id: TASK-67
title: Dataset - Filtrering via objektklasser och datum
status: In Progress
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:31:00Z'
updated_date: '2026-11-12T14:39:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Inför möjlighet att filtrera på objektklasser. Default visas alla men det ska vara möjligt att tex bara visa "pistol"

Det ska även vara möjligt att bara visa data som fångats inom ett datumintervall (via datepickers)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Alla fångster visas som default
- [ ] #2 Klassfiltret visar bara fångster som innehåller vald klass
- [ ] #3 Datumintervallet visar bara fångster som fångats inom intervallet
- [ ] #4 Filtren kan kombineras och nollställas
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
1. Lägg en filterrad överst i datasetvyn: klassval (Alla klasser som default), kryssruta för datumintervall samt två datepickers.
2. Fyll klasslistan och datumgränserna från datasetet vid varje bygge, och behåll användarens val.
3. Filtrera fångsterna i _build: en fångst visas om den innehåller vald klass och ligger inom datumintervallet; osparade fångster filtreras på sina detektioner och sin tidsstämpel.
4. Bygg om listan från redan inläst data när filtret ändras, utan ny filläsning, och visa ett meddelande när inget matchar.
5. Test: default visar allt, klassfiltret, datumintervallet, kombinationen och nollställning.
<!-- SECTION:PLAN:END -->
