---
id: TASK-1
title: Train/val-split per fångstgrupp vid YOLO-export
status: To Do
assignee: []
created_date: '2026-11-06T14:03:00Z'
updated_date: '2026-11-06T14:04:00Z'
labels:
  - arkitektur
  - dataläckage
  - träning
dependencies: []
references:
  - dataset
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Vibe-glm53 exporterar hela datasetet med train=val (100% läckage).

Andra brancher löser detta: opencode-bigpickle (_split_pairs) och opencode-deepseek-flash (prepare_yolo_dataset) delar upp bilderna ca 80/20, SEED-at, och grupperar spliten på fångstparet/capture-gruppen så att vänster- och högerbild från samma ögonblick aldrig hamnar på olika sidor. Se jämförelse_argon.md avsnitt 2:4 och readme-jämförelsen.

Vibe-glm53 har redan capture-group-id i datasetet (group i dataset.json), vilket gör en grupp-medveten split enkel att implementera i dataset/export.py (export_yolo samt ev. export_coco).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 export_yolo() delar upp bilderna i train- och val-uppsättningar (default 80/20, seedat och reproducerbart)
- [ ] #2 bilder med samma group-id hamnar alltid i samma delmängd (train eller val)
- [ ] #3 data.yaml pekar ut train: och val: på olika kataloger
- [ ] #4 träningsvyn visar fördelningen (antal train/val-bilder) innan start
<!-- AC:END -->
