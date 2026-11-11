---
id: TASK-52
title: Detektion - Använd modellens egna klassnamn som källa för detektionens klasser
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T12:49:00Z'
updated_date: '2026-11-11T22:28:00Z'
labels: []
dependencies: []
references:
  - xray_detector/application/model_registry.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
modified_files:
  - xray_detector/infrastructure/detectors/base.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - xray_detector/application/model_registry.py
  - xray_detector/ui/detection_view.py
  - tests/test_model_classes.py
  - tests/test_busy_operations.py
  - tests/test_detection_toggle.py
  - tests/test_detector_settings.py
  - tests/test_model_layout.py
  - tests/test_rfdetr.py
  - README.md
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
- [x] #1 Klassnamnen hämtas från modellen när detektorn laddas, inte från AppConfig.classes
- [x] #2 Detektorn exponerar modellens klassnamn efter laddning så att UI kan lista dem
- [x] #3 AppConfig.classes skickas inte längre som argument till create_detector
- [x] #4 En modell vars klassnamn inte kan läsas ut ger ett tydligt felmeddelande i stället för tysta indexnamn
- [x] #5 Tester täcker klassnamn för både YOLO och RF-DETR
- [x] #6 README beskriver att klassnamnen kommer från modellen
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
1. BaseDetector: class_names är modellens egen lista; detektorerna fyller den vid laddning.
2. YoloDetector läser model.names, RfDetrDetector läser modellens class_names; kan namnen inte läsas kastas ett tydligt ValueError.
3. create_detector(spec, confidence_threshold) tappar class_names-argumentet; DetectionView skickar inte längre config.classes.
4. Tester för YOLO-, RF-DETR- och felläsningsfallet; befintliga fakes uppdateras.
5. README: klassnamnen kommer från modellen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Klassnamnen läses nu ur modellen när detektorn laddas: YoloDetector ur model.names och RfDetrDetector ur modellens class_names (rfdetr 1.7 exponerar dem som en property på detektorn; model_config har inget class_names-fält i den versionen). class_names_from() i base.py normaliserar {index: namn} och listor och kastar ValueError med viktfilens namn när namnen saknas, så en trasig modell ger 'Kunde inte ladda modell: Kunde inte läsa klassnamnen ur ...' i statusraden i stället för indexnamn i overlayn. create_detector(spec, confidence_threshold) tar inte längre emot en klasslista och DetectionView skickar inte config.classes. Verifierat: uv run pytest -q gav 286 passed, 1 skipped (7 nya tester i tests/test_model_classes.py).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Detektorns klassnamn kommer nu från modellen i stället för från AppConfig.classes. YOLO läser model.names och RF-DETR modellens class_names vid laddning; kan namnen inte läsas kastas ett tydligt ValueError som blir 'Kunde inte ladda modell: ...' i statusraden. create_detector tar bara (spec, confidence_threshold), så den döda klasslistan är borta, och AppConfig.classes beskriver fortsatt datasetets etiketter. Nya tester i tests/test_model_classes.py täcker båda familjerna, felläsningen och att vyn inte skickar appens klasslista; hela sviten gick grönt (286 passed, 1 skipped). README beskriver källan till klassnamnen.
<!-- SECTION:FINAL_SUMMARY:END -->
