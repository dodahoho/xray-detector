---
id: TASK-172
title: RF-DETR tappar alla detektioner när modellens klassnamn är mojibake
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-20T19:45:00Z'
updated_date: '2026-11-20T20:04:00Z'
labels: []
dependencies: []
type: bug
ordinal: 464000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Efter TASK-165 (repair_mojibake i class_names_from) detekterar en egentränad RF-DETR-modell ingenting i detektionsvyn, trots att modellen hittar objekten. class_names_from rättar modellens klasslista till 'löpare', men RfDetrDetector._class_name returnerar result.data['class_name'] orättat ('lÃ¶pare') från rfdetr:s egen lista. BaseDetector.filter_detections jämför detektionens class_name mot enabled_classes, och när namnen inte matchar filtreras varje detektion bort. YOLO påverkas inte, eftersom dess _class_name läser detektorns redan rättade class_names. Modeller tränade på en export vars COCO-kategorier skrevs före TASK-165 bär mojibake i vikterna, så felet slår igenom för alla sådana snapshots.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 En RF-DETR-modell vars vikter har klassnamnet 'lÃ¶pare' ger detektioner med class_name 'löpare'
- [x] #2 Detektionerna överlever BaseDetector.filter_detections när enabled_classes är modellens class_names
- [x] #3 Ett regressionstest i tests/test_class_encoding.py täcker RF-DETR:s klassnamn i detektionsvägen
- [x] #4 Hela testsviten passerar
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
1. Rätta klassnamnet i RfDetrDetector._class_name med repair_mojibake, så detektionens class_name hamnar i samma namnrymd som detektorns class_names.
2. Regressionstest i tests/test_class_encoding.py: en detektion med mojibake-namn överlever filter_detections när enabled_classes är modellens rättade class_names.
3. Kör testsviten.
4. Verifiera mot den tränade modellen och videofilerna i media/.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rotorsak: pycocotools.coco.COCO läser _annotations.coco.json med open(path, 'r') utan encoding, alltså cp1252 på den här maskinen. Exporten skriver korrekt UTF-8 (löpare), men rfdetr:s datamodul får klassnamnet via coco.cats och där blir det lÃ¶pare. Namnet följer med in i model.class_names och checkpointen. class_names_from rättar detektorns lista till löpare, medan RfDetrDetector._class_name returnerade rfdetr:s orättade namn. BaseDetector.filter_detections jämför de två och släppte igenom noll detektioner.

Verifiering: mot models/trained/2026-11-20_193937 och 2026-11-20_193320 på media/xray_slideshow_top.mp4 och xray_slideshow_side.mp4 behåller detektionerna nu klassfiltret (25/19 respektive 28/19 detektioner på 8 samplade ramar) med class_name löpare. Före rättningen gav samma körning 1 rå detektion och 0 efter filtret. Regressionstestet faller utan rättningen (assert [] == ['löpare']) och passerar med den.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RfDetrDetector._class_name rättar nu klassnamnet med repair_mojibake, så detektionens class_name hamnar i samma namnrymd som detektorns class_names. Utan rättningen jämförde BaseDetector.filter_detections 'lÃ¶pare' mot 'löpare', och varje detektion filtrerades bort.

Bakgrund: pycocotools läser _annotations.coco.json med open(path, 'r') utan encoding, alltså cp1252 på Windows. Exporten skriver korrekt UTF-8, men rfdetr:s datamodul får klassnamnet via coco.cats och lagrar mojibake i model.class_names och checkpointen. class_names_from rättade redan detektorns lista; detektionens namn saknades.

Verifiering: 1031 passed, 1 skipped i hela sviten. Regressionstestet faller utan rättningen (assert [] == ['löpare']). Mot 2026-11-20_193937 och 2026-11-20_193320 på media/xray_slideshow_top.mp4 och xray_slideshow_side.mp4 behåller detektionerna filtret (25/19 respektive 28/19 på 8 samplade ramar) med class_name löpare, mot 1 rå detektion och 0 efter filtret före rättningen.

Kvarstående risk: mojibaken uppstår fortfarande i rfdetr/pycocotools vid varje träning på Windows, så rättningen i detektorn behövs permanent. En framtida åtgärd kan vara att skriva exportens kategorier som ASCII-säkra eller att sätta PYTHONUTF8=1 i träningsprocessen.
<!-- SECTION:FINAL_SUMMARY:END -->
