---
id: TASK-65
title: Dataset - Hela card är klickbart
status: In Progress
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:24:00Z'
updated_date: '2026-11-12T14:36:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 63000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
För att markera ett card med bildpar går det nu att klicka på någon av bilderna, men det skulle vara bättre att man istället har hela ytan som utgör ett card som klickbar
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Ett klick var som helst på kortet markerar hela fångsten
- [ ] #2 Ett klick på en thumbnail markerar fångsten en gång, inte två
- [ ] #3 Kortet behåller sin storlek när fångsten markeras
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
1. Inför CaptureCard, en QFrame som äger fångstens group_id och sänder clicked vid musklick.
2. Låt både sparade och osparade kort använda CaptureCard och koppla clicked till samma växling som thumbnails använder.
3. Gör rubrikraden genomsläpplig för musklick, så klick på tid och klassmärken når kortet.
4. Test: klick på kortets yta markerar hela fångsten, klick på en thumbnail växlar bara en gång, och kortets storlek är oförändrad.
<!-- SECTION:PLAN:END -->
