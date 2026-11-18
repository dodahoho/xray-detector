---
id: TASK-155
title: Ersätt QtCharts med QPainter-graf, byt fourcc-anrop, utvärdera opencv-headless
status: In Progress
assignee: []
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-18T09:04:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
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
- [ ] #1 Inget beroende av PySide6.QtCharts finns kvar; träningsgraferna följer ljust och mörkt tema
- [ ] #2 cv2.VideoWriter.fourcc används överallt
- [ ] #3 Beslut om opencv-python-headless är dokumenterat efter kontroll av kamerastöd på Windows
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
