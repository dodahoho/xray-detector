---
id: TASK-94
title: Train/val-delningen är inte stratifierad på objektklasser
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:26:00Z'
updated_date: '2026-11-16T19:18:00Z'
labels: []
dependencies: []
priority: medium
type: enhancement
ordinal: 209000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-89. `export.py:train_val_split` blandar fångstgrupper slumpmässigt med seed 42. Grupperingen hindrar läckage mellan train och val, vilket är rätt, men det finns ingen stratifiering: en ovanlig klass kan hamna helt utanför val, och då mäter val-mAP inte det den ser ut att mäta. Risken växer när datasetet är litet eller när en klass har få exempel. xray_modeltrainer stratifierar på klassuppsättningssignatur och lägger de minsta grupperna först, så att ovanliga klasser inte svälts av avrundning.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Varje klass som finns i datasetet finns representerad i både train och val när den har tillräckligt många exempel
- [x] #2 Delningen sker fortfarande per fångstgrupp så att bildpar inte splittras
- [x] #3 Delningen är reproducerbar med samma seed
- [x] #4 Test täcker att en klass med få exempel hamnar i båda delmängderna
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
1. Stratifiera train_val_split på klassuppsättningssignatur per fångstgrupp.
2. Minsta signaturerna först och girig tilldelning mot delarnas målantal, så en ovanlig klass hamnar i både train och val.
3. Behåll gruppdelningen (bildpar splittras aldrig) och reproducerbarheten med samma seed.
4. Test som visar att en klass med få exempel hamnar i båda delmängderna.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- export.py: _class_group_counts(), _rarity_key() och _stratified_order(). Grupper med den ovanligaste klassen läggs först i kön (minsta antal grupper för klasserna i gruppen), ordningen inom samma ovanlighet är seedad.
- _assign()/_next_split() fördelar varje grupp till den del som ligger längst efter sin andel, så en klass med två grupper hamnar i både train och val. Målantalen räknas som tidigare (round(total * ratio)), så andelen ger samma antal bildpar som förut.
- Negativa exempel saknar klass och läggs sist i kön.

Verifiering: tests/test_export_split.py täcker att en klass med få exempel hamnar i båda delmängderna, att grupperna hålls ihop och att delningen är reproducerbar. Befintliga tester för andelen (5/1, 3/3, 5/5) är oförändrade. Hela sviten: 747 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Train/val-delningen är stratifierad på klassuppsättning. Grupper som innehåller en ovanlig klass läggs först i kön och fördelas mot delarnas målantal, så en klass som bara finns i två bildpar hamnar i både train och val i stället för att falla utanför val. Målantalen räknas som förut (round(total * ratio)), så andelen ger samma antal bildpar som tidigare — 6 par vid 80 % ger fortfarande 5/1 och 10 par vid 50 % ger 5/5. Delningen sker fortfarande per fångstgrupp, så ett bildpar splittras aldrig, och ordningen inom samma ovanlighet är seedad så samma seed ger samma delning. Negativa exempel saknar klass och läggs sist i kön.

Verifiering: tests/test_export_split.py täcker att en klass med få exempel hamnar i båda delmängderna, att grupperna hålls ihop och att delningen är reproducerbar; de befintliga testerna för andelen är oförändrade. Hela sviten: 747 passed, 1 skipped.

Begränsning: en klass som bara finns i en enda grupp kan inte hamna i båda delmängderna utan att splittra gruppen, och då vinner gruppintegriteten.
<!-- SECTION:FINAL_SUMMARY:END -->
