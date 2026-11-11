---
id: TASK-53
title: Detektion - Välj vilka klasser som ska detekteras, per modell
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T12:49:00Z'
updated_date: '2026-11-11T22:33:00Z'
labels: []
dependencies:
  - TASK-52
references:
  - xray_detector/ui/detection_view.py
  - xray_detector/infrastructure/detectors/base.py
modified_files:
  - xray_detector/infrastructure/detectors/base.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - xray_detector/ui/settings_dialog.py
  - xray_detector/ui/detection_view.py
  - tests/test_class_filter.py
  - tests/test_settings_dialog.py
  - tests/test_detector_settings.py
  - tests/test_model_layout.py
  - tests/test_rfdetr.py
  - README.md
priority: high
type: feature
ordinal: 51000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
En modell kan detektera många klasser (yolo26n är tränad på 80 COCO-klasser) och användaren vill bara se en delmängd av dem. I dag finns ingen filtrering: allt modellen hittar ritas i overlayen. Klasslistan skiljer sig mellan modeller, så inställningarna kan inte vara en fast lista — de måste följa vald modell. Alla klasser ska vara påslagna från början så att beteendet är oförändrat tills användaren aktivt klickar bort något. Bygger på att detektorn exponerar modellens klassnamn (TASK-52).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Detektionsinställningarna listar alla klasser som vald modell kan detektera
- [ ] #2 Alla klasser är valda när en modell laddas första gången
- [ ] #3 Bortvalda klasser ger inga detektioner i overlayen
- [ ] #4 Klasslistan i inställningarna uppdateras när användaren byter modell
- [ ] #5 Valen sparas per modell så att de finns kvar när man byter tillbaka
- [ ] #6 Klasser som tillkommer i en modell visas som valda
- [ ] #7 Om alla klasser väljs bort visas ett tydligt meddelande och ingen detektion körs
- [ ] #8 Tester täcker filtrering, modellbyte och persistens
- [ ] #9 README beskriver klassfiltret
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
1. BaseDetector får set_enabled_classes() och filter_detections(); YOLO och RF-DETR filtrerar sina detektioner innan de returneras.
2. ClassFilterSection i settings_dialog.py: en kryssruta per klass som vald modell kan detektera, plus en varning när ingen klass är vald.
3. DetectionView: detektionsvyns inställningsknapp öppnar sektionen, klassnamnen cachas per modell när detektorn laddas, och bortvalda klasser sparas per modell (detection/classes_off/<modellnyckel>). Nya klasser i en modell är därför valda från början.
4. Klassfiltret appliceras när modellen laddas och när ett val ändras; är alla klasser bortvalda kopplas detektorn bort och ett tydligt meddelande visas.
5. Tester för filtrering, modellbyte, persistens och alla-av; README beskriver klassfiltret.
<!-- SECTION:PLAN:END -->
