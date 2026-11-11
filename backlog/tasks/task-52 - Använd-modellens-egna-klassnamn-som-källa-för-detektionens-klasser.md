---
id: TASK-52
title: Detektion - Använd modellens egna klassnamn som källa för detektionens klasser
status: To Do
assignee: []
created_date: '2026-11-11T12:49:00Z'
updated_date: '2026-11-11T20:23:00Z'
labels: []
dependencies: []
references:
  - xray_detector/application/model_registry.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
priority: high
type: bug
ordinal: 50000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Detektionsvyn skickar AppConfig.classes (cigaretter, cannabis, kniv, pistol) till create_detector, men YoloDetector.detect() läser klassnamnen ur result.names och RfDetrDetector använder den inskickade listan bara som fallback när modellen inte anger något namn. Listan som skickas in är alltså i praktiken död för YOLO och kan ge fel namn för RF-DETR. Modellens egna klassnamn finns i viktfilen (YOLO: model.names, RF-DETR: model.model_config.class_names) och är den enda källan som stämmer med vad modellen faktiskt kan detektera. AppConfig.classes ska fortsätta beskriva datasetets etiketter (annotering, DatasetService, overlayfärger) — det är en annan sak än modellens klasslista och ska inte blandas ihop med den.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Klassnamnen hämtas från modellen när detektorn laddas, inte från AppConfig.classes
- [ ] #2 Detektorn exponerar modellens klassnamn efter laddning så att UI kan lista dem
- [ ] #3 AppConfig.classes skickas inte längre som argument till create_detector
- [ ] #4 En modell vars klassnamn inte kan läsas ut ger ett tydligt felmeddelande i stället för tysta indexnamn
- [ ] #5 Tester täcker klassnamn för både YOLO och RF-DETR
- [ ] #6 README beskriver att klassnamnen kommer från modellen
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
