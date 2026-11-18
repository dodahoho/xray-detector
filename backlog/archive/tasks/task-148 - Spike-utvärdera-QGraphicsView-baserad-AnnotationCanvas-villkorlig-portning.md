---
id: TASK-148
title: 'Spike: utvärdera QGraphicsView-baserad AnnotationCanvas (villkorlig portning)'
status: To Do
assignee: []
created_date: '2026-11-17T20:53:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
priority: low
type: spike
ordinal: 146000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
AnnotationCanvas i ui/annotation_view.py är ~400 rader manuell koordinattransformation som skalas om på CPU i varje paintEvent. TASK-21-spiken utvärderade QGraphicsScene men portades aldrig. Portning är bara aktuell om fler funktioner planeras (polygoner, mätverktyg, kontrastreglage) (utvärdering_argon.md §6.1, utvärdering_hydrogen.md §5.1).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Beslut är dokumenterat med motivering: porta till QGraphicsView eller behåll AnnotationCanvas
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
