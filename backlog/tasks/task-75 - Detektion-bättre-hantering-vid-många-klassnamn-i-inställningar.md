---
id: TASK-75
title: Detektion - bättre hantering vid många klassnamn i inställningar
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T20:12:00Z'
updated_date: '2026-11-12T20:33:00Z'
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
- [x] #1 Klasslistan i detektionens inställningar visar många klasser (COCO-80) i flera kolumner i stället för en enda lång rad
- [x] #2 Listan får en rullist när klasserna inte ryms i dialogrutan, så inga klassnamn hamnar utanför skärmen
- [x] #3 Valet av klasser fungerar som förut: bortval sparas per modell och varningen visas när inga klasser är valda
- [x] #4 Testerna för klassfiltret och inställningsdialogen passerar
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
1. ClassFilterSection lägger kryssrutorna i ett QGridLayout med fast kolumnantal i stället för en QVBoxLayout.

2. Rutnätet ligger i en QScrollArea med högsta höjd, så listan rullar i stället för att växa utanför skärmen.

3. Nya tester för kolumnplacering, rullistan och oförändrat valbeteende; README uppdateras.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ClassFilterSection lägger kryssrutorna i ett QGridLayout med CLASS_COLUMNS=5 kolumner i en QScrollArea med CLASS_LIST_MAX_HEIGHT=420. Rullistans minimumWidth räknas ur rutnätets sizeHint plus den vertikala rullistens bredd och ramen, så alla kolumner syns och bara höjden rullar. Mätt med COCO-80: dialogrutan blir 602x482 px, vertikal rullist syns, ingen horisontell. Med två klasser blir rutnätet en rad och ingen rullist visas.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Klassfiltret i detektionens inställningar listar modellens klasser i ett rutnät med fem kolumner i en rullista med högsta höjd 420 px, i stället för en enda lång kolumn som växte utanför skärmen. Rullistan är dimensionerad så att alla kolumner syns; bara höjden rullar. Valet av klasser är oförändrat: bortval sparas per modell och varningen visas när inga klasser är valda. Verifierat: test_section_lays_the_classes_out_in_columns (rad- och kolumnplacering), test_section_scrolls_when_the_classes_do_not_fit (80 klasser ger vertikal rullist, ingen horisontell, dialoghöjd under gränsen), test_section_with_few_classes_does_not_scroll samt de befintliga testerna i test_class_filter.py för val, sparning per modell och varning. Mätt manuellt med COCO-80: dialogrutan blir 602x482 px. Hela sviten: 503 passed, 1 skipped. README beskriver listan.
<!-- SECTION:FINAL_SUMMARY:END -->
