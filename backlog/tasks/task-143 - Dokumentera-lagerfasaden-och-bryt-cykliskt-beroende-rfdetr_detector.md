---
id: TASK-143
title: Dokumentera lagerfasaden och bryt cykliskt beroende rfdetr_detector
status: To Do
assignee: []
created_date: '2026-11-17T20:52:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
priority: medium
type: enhancement
ordinal: 141000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ui importerar infrastructure på fem ställen, application importerar infrastructure i fem av åtta moduler, och rfdetr_detector.py importerar application.app_config (cykliskt) (alla tre utvärderingarna). Vid motsägelsen mellan strukturell ombyggnad och dokumentation väljs enklaste först: dokumentera i README/groma att application är en fasad bredvid infrastructure och vilka importregler som gäller; flytta augment-konstanter (MIN_SCALE/MAX_SCALE/describe) till domain/dataset.py; bryt det cykliska beroendet genom att flytta loggfångsten till infrastructure/logging.py eller en callback.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README/groma beskriver tydligt att application är en fasad och vilka importregler som gäller
- [ ] #2 Inget cykliskt beroende infrastructure -> application finns kvar
- [ ] #3 MIN_SCALE/MAX_SCALE/describe ligger i domain/dataset.py och ui importerar dem därifrån
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
