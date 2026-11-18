---
id: TASK-151
title: >-
  Prestanda: kör datasetexport vid träningsstart i BackgroundTask och vid
  faktisk start för schemalagda jobb
status: In Progress
assignee: []
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-18T07:26:00Z'
labels:
  - performance
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
priority: low
type: enhancement
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Export vid träningsstart körs synkront i GUI-tråden (raderar exports/ och kopierar alla bilder); schemalagda jobb exporterar vid klickögonblicket så dagens annoteringar missas; för YOLO behövs ingen bildkopiering alls om data.yaml pekar på train.txt/val.txt (utvärdering_argon.md §5.3). Flytta exporten till BackgroundTask och kör den när det schemalagda jobbet faktiskt startar.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GUI-tråden fryser inte vid träningsstart (export körs i bakgrunden)
- [ ] #2 Schemalagd träning exporterar datasetet när jobbet startar, inte vid schemaläggning
- [ ] #3 YOLO-träning använder train.txt/val.txt utan att kopiera bilder
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
