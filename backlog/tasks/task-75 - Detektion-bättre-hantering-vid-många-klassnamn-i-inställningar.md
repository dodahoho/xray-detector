---
id: TASK-75
title: Detektion - bättre hantering vid många klassnamn i inställningar
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-12T20:12:00Z'
updated_date: '2026-11-12T20:31:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/settings_dialog.py
  - tests/test_class_filter.py
  - README.md
type: bug
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TOLO och RF-DETR är tränade på COCO-80 dataset som innehåller 80 st klassnamn. Det blir en för lång lista i inställningarna där man kan välja klassnamn att detektera. Som det är nu hamnar många klassnamn helt utanför skärmen. Det måste göras på nåt annat sätt som klara av hundratals klassnamn, t ex listas i flera kolumner i en bredare dialogruta och eventuellt ha scollbars om innehållet inte ryms i dialogrutan.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Klasslistan i detektionens inställningar visar många klasser (COCO-80) i flera kolumner i stället för en enda lång rad
- [ ] #2 Listan får en rullist när klasserna inte ryms i dialogrutan, så inga klassnamn hamnar utanför skärmen
- [ ] #3 Valet av klasser fungerar som förut: bortval sparas per modell och varningen visas när inga klasser är valda
- [ ] #4 Testerna för klassfiltret och inställningsdialogen passerar
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
1. ClassFilterSection lägger kryssrutorna i ett QGridLayout med fast kolumnantal i stället för en QVBoxLayout.

2. Rutnätet ligger i en QScrollArea med högsta höjd, så listan rullar i stället för att växa utanför skärmen.

3. Nya tester för kolumnplacering, rullistan och oförändrat valbeteende; README uppdateras.
<!-- SECTION:PLAN:END -->
