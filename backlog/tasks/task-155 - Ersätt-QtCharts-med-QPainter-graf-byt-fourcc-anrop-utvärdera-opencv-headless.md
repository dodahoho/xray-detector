---
id: TASK-155
title: Ersätt QtCharts med QPainter-graf, byt fourcc-anrop, utvärdera opencv-headless
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-18T09:14:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
documentation:
  - doc-1
modified_files:
  - xray_detector/ui/training_chart.py
  - tests/test_training_chart.py
  - xray_detector/infrastructure/video/source.py
  - tests/conftest.py
  - tests/test_video_modes.py
  - README.md
  - backlog/docs/doc-1 - Beslut-opencv-python-headless.md
  - groma/systems/xray-detector/containers/gui-app/components/training-chart.md
priority: low
type: enhancement
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PySide6.QtCharts är deprecated i Qt 6.8 och borttagen i 6.10, och QChart i training_chart.py följer inte appens tema (vit bakgrund även i mörkt läge) (utvärdering_argon.md §6.1). Ersätt med en enkel egen QWidget som ritar axlar/polylinjer med QPainter och använder self.palette(). Byt även cv2.VideoWriter_fourcc till cv2.VideoWriter.fourcc (source.py, conftest.py). Utvärdera opencv-python-headless (kontrollera DirectShow/MSMF-stöd på Windows innan byte) (argon + hydrogen).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Inget beroende av PySide6.QtCharts finns kvar; träningsgraferna följer ljust och mörkt tema
- [x] #2 cv2.VideoWriter.fourcc används överallt
- [x] #3 Beslut om opencv-python-headless är dokumenterat efter kontroll av kamerastöd på Windows
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
1. Skriv om ui/training_chart.py: Series/Axis som dataklasser och LineChart(QWidget) som ritar axlar, rutnät, polylinjer, markörer och legend med QPainter; färger ur self.palette() så ljust/mörkt tema följer med. TrainingChart behåller add_epoch/clear/has_data.
2. Uppdatera tests/test_training_chart.py till den nya API:n och lägg till ett tematest som renderar grafen med ljus respektive mörk palett.
3. Byt cv2.VideoWriter_fourcc mot cv2.VideoWriter.fourcc i infrastructure/video/source.py, tests/conftest.py och tests/test_video_modes.py.
4. Verifiera DirectShow/MSMF med den installerade opencv-byggnaden och dokumentera beslutet om opencv-python-headless som en backlog decision.
5. Uppdatera README-raden om QtCharts och groma-beskrivningen av training-chart; kör ruff och pytest.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TrainingChart ritar nu med QPainter: Series/Axis som dataklasser och LineChart(QWidget) med axlar, rutnät, polylinjer, markörer och legend. Bakgrund, text och rutnät hämtas ur self.palette(), så grafen följer ljust och mörkt tema; tematester renderar widgeten med båda paletterna. cv2.VideoWriter_fourcc är bytt mot cv2.VideoWriter.fourcc i source.py, conftest.py och test_video_modes.py. Beslutet om opencv-python-headless finns i doc-1: kvar som opencv-python, eftersom ultralytics kräver det och DirectShow/MSMF är verifierat i headless-byggnaden.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TrainingChart ritar nu två grafer med QPainter i stället för QtCharts: Series och Axis är dataklasser och LineChart ritar axlar med runda tickvärden, rutnät, polylinjer, markörer och legend. Bakgrund, text och rutnät hämtas ur widgetens palett, så grafen följer ljust och mörkt tema; två tematester renderar widgeten med båda paletterna och kontrollerar bakgrunds- och textfärgen. cv2.VideoWriter_fourcc är bytt mot cv2.VideoWriter.fourcc i source.py, conftest.py och test_video_modes.py. Beslutet om opencv-python-headless finns i doc-1: den direkta dependencyn är kvar som opencv-python, eftersom ultralytics kräver det och två hjul som äger samma cv2-katalog skulle göra vinnaren beroende av installationsordningen. Kamerastödet är verifierat: den installerade headless-byggnaden (GUI: NONE) rapporterar DirectShow: YES och öppnade en riktig kamera via CAP_DSHOW. Verifiering: ruff check . är ren och pytest -q -n auto ger 892 passed, 4 failed; de fyra felen (test_app_icon och tre i test_detection_badge) finns även på HEAD utan denna ändring och beror på att miljön saknar teckensnitt, inte på ändringen.
<!-- SECTION:FINAL_SUMMARY:END -->
