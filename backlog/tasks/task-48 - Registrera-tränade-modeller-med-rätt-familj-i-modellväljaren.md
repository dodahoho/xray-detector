---
id: TASK-48
title: Registrera tränade modeller med rätt familj i modellväljaren
status: To Do
assignee: []
created_date: '2026-11-11T11:51:00Z'
labels: []
dependencies:
  - TASK-47
references:
  - xray_detector/application/model_registry.py
  - xray_detector/ui/detection_view.py
priority: medium
type: bug
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
trained_models i application/model_registry.py skapar alltid ModelSpec(..., family="yolo", ...), oavsett vad manifestet säger. En RF-DETR-körning registreras därför som YOLO och laddas med YoloDetector, vilket misslyckas när vikterna är en .pth. Det gör RF-DETR-snapshots oanvändbara i modellväljaren, även om TASK-47 sparar dem korrekt.

Manifestet behöver familjen (TASK-47) och trained_models ska använda den. Saknas familj i ett äldre manifest ska beteendet vara bakåtkompatibelt.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Manifestet anger modellfamilj
- [ ] #2 trained_models använder manifestets familj i stället för hårdkodad yolo
- [ ] #3 En RF-DETR-snapshot laddas med RfDetrDetector i modellväljaren
- [ ] #4 En YOLO-snapshot laddas med YoloDetector som förut
- [ ] #5 Äldre manifest utan familj fungerar fortfarande
- [ ] #6 Tester täcker båda familjerna
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
