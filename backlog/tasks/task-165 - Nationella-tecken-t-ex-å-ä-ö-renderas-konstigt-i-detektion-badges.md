---
id: TASK-165
title: Nationella tecken (t ex å ä ö) renderas konstigt i detektion badges
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-19T22:13:00Z'
updated_date: '2026-11-20T11:11:00Z'
labels: []
dependencies: []
type: bug
ordinal: 301000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När dataset har objektklass med svenska tecknena å ä och ö (gäller förmodligen även andra tecken utanför engelska alfabetet) renderas de konstigt när en tränad modell senare kör i detektionsläge.

Nånstans i kedjan dataset, träning, detektion blir det en inkompabilitet i teckenuppsättningarna.

Objektklassen "löpare" i dataset, blir "lÃ¶pare" i badge när modellen har tränats och kör i detektionsläge.
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
1. Reparera mojibake i klassnamn vid läsning: en hjälpare i domain som tolkar UTF-8-byten som lästs som latin-1 (lÃ¶pare -> löpare).
2. Använd hjälparen i read_classes (datasetets data.yaml) och class_names_from (modellens klassnamn), så både dataset, export, träning och badge får rätt namn.
3. Tester för hjälparen och för de två läsarna.
4. Kör testsviten och verifiera mot det befintliga datasetet.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rotorsak: ett klassnamn kunde hamna i datasetets data.yaml som mojibake (UTF-8-byten lästa som latin-1), t.ex. lÃ¶pare i stället för löpare. Namnet följde sedan med till exporten, träningsmanifestet och modellens vikter, och klassmärket visade fel tecken.

Åtgärd: repair_mojibake i domain/dataset.py tolkar texten som latin-1-kodade UTF-8-byten när det går och lämnar annars namnet orört. Den används i read_classes (datasetets data.yaml), write_data_yaml (så filen läker nästa gång den skrivs), class_names_from (modellens klassnamn, både YOLO och RF-DETR) och _read_data_classes (RF-DETR-exportens COCO-kategorier).

Verifiering: nya tests/test_class_encoding.py (11 tester) plus hela sviten: 1001 passed, 1 skipped. Mot det befintliga datasetet och modellen 2026-11-20_093526 ger read_classes och class_names_from nu löpare (0xF6) för båda posterna i stället för lÃ¶pare.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Klassnamn som sparats som UTF-8 men lästs som latin-1 (lÃ¶pare i stället för löpare) rättas nu när de läses. repair_mojibake i domain/dataset.py tolkar texten som latin-1-kodade UTF-8-byten när det går och lämnar annars namnet orört. Den används i read_classes (datasetets data.yaml), write_data_yaml (filen läker nästa gång den skrivs), class_names_from (modellens klassnamn för YOLO och RF-DETR) och _read_data_classes (RF-DETR-exportens COCO-kategorier). Därmed visar datasetvyn, exporten, träningsmanifestet och klassmärket samma tecken.

Verifiering: nya tests/test_class_encoding.py med 11 tester, och hela sviten gick igenom (1001 passed, 1 skipped). Mot det befintliga datasetet och modellen 2026-11-20_093526 returnerar read_classes och class_names_from nu löpare (0xF6) för båda posterna i stället för lÃ¶pare. Ruff är grönt på de ändrade filerna.

Kvar att känna till: en modell som tränats med både löpare och lÃ¶pare får två poster med samma namn efter rättningen; det är ett dataproblem i den modellen, inte i visningen. Datasetets data.yaml rättas på disk först nästa gång klasslistan skrivs.
<!-- SECTION:FINAL_SUMMARY:END -->
