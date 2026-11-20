---
id: TASK-128
title: 'Trådsäkerhet i detektion: lås runt detect() och stoppa source_lost-loop'
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:15:00Z'
labels:
  - bugfix
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
modified_files:
  - xray_detector/infrastructure/detectors/base.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - xray_detector/infrastructure/video/camera_service.py
  - xray_detector/ui/detection_view.py
  - tests/conftest.py
  - tests/test_detector_threading.py
priority: high
type: bug
ordinal: 333000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Samma BaseDetector-instans delas av två StreamWorker-trådar som anropar detect() parallellt utan lås (Ultralytics YOLO.predict är inte trådsäkert på samma instans); enabled_classes/confidence_threshold muteras samtidigt från GUI-tråden (utvärdering_argon.md §5.2, utvärdering_hydrogen.md §5.4). Dessutom loopar StreamWorker source_lost var 500:e ms i evighet efter read()==None, och StreamPanel._to_qimage returnerar QImage utan .copy(). Lägg threading.Lock runt detect(), avsluta loopen vid None, använd QThread.isInterruptionRequested(), returnera .copy().
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Samtidiga detect()-anrop på samma detektor serialiseras utan race conditions eller krascher
- [x] #2 StreamWorker avslutar loopen när read() returnerar None (inga upprepade source_lost-signaler)
- [x] #3 StreamPanel._to_qimage returnerar en ägd kopia (.copy())
- [x] #4 Test täcker samtidig detect från två trådar
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
1. BaseDetector: threading.RLock som serialiserar detect() och skyddar enabled_classes/confidence_threshold; detect() blir publik wrapper runt en abstrakt _detect().

2. StreamWorker: avsluta loopen när read() ger None i stället för att signalera source_lost var 500:e ms, och använd isInterruptionRequested()/requestInterruption() i stället för den egna _running-flaggan.

3. StreamPanel._to_qimage returnerar .copy() så QImage äger sina pixlar.

4. Ny testsvit tests/test_detector_threading.py: samtidiga detect-anrop, inställningsändringar under detektion, source_lost en gång, stop() och .copy().
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
base.py: detect() tar RLock och delegerar till den abstrakta _detect(), så en underklass inte kan glömma låset. RLock krävs eftersom yolo_detector och rfdetr_detector anropar filter_detections() inifrån detect(). set_confidence_threshold, set_enabled_classes och filter_detections tar samma lås, så GUI-trådens ändringar inte kan slås sönder av ett pågående anrop. Underklasserna och FakeDetector i conftest implementerar _detect.

camera_service.py: loopen bryter med return när read() ger None, så source_lost signaleras en gång och tråden avslutas; panelen begär en ny källa när den vill återansluta. _running är borta till förmån för isInterruptionRequested()/requestInterruption(). detection_view.py: _to_qimage avslutar med .copy().

Verifiering: tests/test_detector_threading.py har 7 tester. Med låset borttaget fallerar tre av dem med max_active 2 respektive 4, så de fångar verkligen racet. Hela sviten: 874 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Detektionen är trådsäker: BaseDetector serialiserar detect() med ett RLock och skyddar enabled_classes/confidence_threshold med samma lås, så två strömtrådar och GUI-tråden inte längre kan krocka på en delad detektor. StreamWorker avslutar loopen när read() ger None i stället för att signalera source_lost i evighet, och använder QThreads avbrottsflagga. StreamPanel._to_qimage lämnar en ägd kopia. Sju nya tester i tests/test_detector_threading.py; tre av dem fallerar om låset tas bort. Hela sviten: 874 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
