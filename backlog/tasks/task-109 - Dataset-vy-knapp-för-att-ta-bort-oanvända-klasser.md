---
id: TASK-109
title: Dataset vy - knapp för att ta bort oanvända klasser
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T08:19:00Z'
updated_date: '2026-11-17T09:07:00Z'
labels: []
dependencies: []
type: feature
ordinal: 359000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lägg till en ny knapp på samma rad som övriga men med padding till övriga så att det upplevs som en egen knappgrupp

Knappen ska ta bort oanvända objektklasser, dvs rensa klasslistan för dataset så att det endast är kvar objektklasser som finns annoterade
<!-- SECTION:DESCRIPTION:END -->

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
1. DatasetStore.unused_classes() räknar i en svepning över labels/ vilka klasser som är annoterade, och remove_unused_classes() skriver om data.yaml till bara dem.
2. DatasetService exponerar båda.
3. Datasetvyn får knappen "Ta bort oanvända klasser" med eget mellanrum (BUTTON_GROUP_GAP) före, så den läses som en egen grupp. Bekräftelsedialog med antalet och namnen, statusrad när inget finns att ta bort.
4. Tester: borttagning räknar om labelindexen, klasser som används blir kvar, och knappen finns i vyn.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
DatasetStore.unused_classes() läser labels/ i en svepning och jämför med data.yaml, i stället för en sökning per klass som class_in_use() gör. remove_unused_classes() skriver om klasslistan via set_classes(), som också skriver om labelindexen, så de kvarvarande klasserna behåller sina annoteringar.

Knappen ligger sist på knappraden med BUTTON_GROUP_GAP före, så den läses som en egen grupp. Mnemonik Alt+K (klasser); Alt+T krockade med flikgenvägarna. Dialogen listar namnen och antalet, och när inget är oanvänt säger statusraden det i stället för att öppna en dialog.

Verifierat: 4 nya tester i tests/test_dataset_store.py och 4 i tests/test_dataset_classes.py (knappen finns, tar bort, klassfiltret följer med, avböjd dialog lämnar listan orörd). Hela sviten: 812 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetvyn har fått knappen Ta bort oanvända klasser (Alt+K) som en egen grupp sist på knappraden. Den rensar datasetets klasslista till de klasser som finns annoterade och skriver om labelindexen, så de kvarvarande klasserna behåller sina annoteringar. Klasserna läses i en svepning över labels/ i stället för en sökning per klass.

Dialogen visar antalet och namnen, och när inget är oanvänt säger statusraden det i stället för att öppna en dialog. Klassfiltret i vyn följer den rensade listan.

Verifierat med 8 nya tester: unused_classes/remove_unused_classes på lagringen (inklusive att annoteringarna följer med och att en använd klass inte tas bort), och knappen i vyn (finns, tar bort, uppdaterar filtret, avböjd dialog lämnar listan orörd). Hela sviten: 812 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
