---
id: TASK-75
title: Detektion - bättre hantering vid många klassnamn i inställningar
status: To Do
assignee: []
created_date: '2026-11-12T20:12:00Z'
labels: []
dependencies: []
type: bug
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TOLO och RF-DETR är tränade på COCO-80 dataset som innehåller 80 st klassnamn. Det blir en för lång lista i inställningarna där man kan välja klassnamn att detektera. Som det är nu hamnar många klassnamn helt utanför skärmen. Det måste göras på nåt annat sätt som klara av hundratals klassnamn, t ex listas i flera kolumner i en bredare dialogruta och eventuellt ha scollbars om innehållet inte ryms i dialogrutan.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
