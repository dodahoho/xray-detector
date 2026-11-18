---
id: TASK-153
title: Kurera groma/-arkitekturen och arkivera klara backlog-tasks
status: To Do
assignee: []
created_date: '2026-11-17T20:54:00Z'
labels:
  - docs
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
priority: low
type: docs
ordinal: 151000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
groma/ har trasiga pre-TASK-22-sökvägar och länkar (detectors.md, video-capture.md, dataset.md, trainer.md), felplacerade/okurerade komponenter (model-input.md, training-history.md, ui-training-history.md) och saknar komponenter för application/evaluation.py, augment.py, metrics.py, progress.py, verdict.py, ui/variation_dialog.py (utvärdering_argon.md §8.2). Kurera via groma-CLI (inte direkt filredigering). Arkivera även de 114+ klara tasks i backlog/tasks/ till backlog/archive/tasks/ via backlog-CLI.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Inga trasiga källkodsreferenser eller länkar finns kvar i groma/; saknade moduler är tillagda som komponenter
- [ ] #2 Klara backlog-tasks är arkiverade via backlog task archive
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
