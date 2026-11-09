---
id: TASK-1
title: Train/val-split per fångstgrupp vid YOLO-export
status: Done
assignee:
  - '@glm53'
created_date: '2026-11-06T14:03:00Z'
updated_date: '2026-11-09T09:30:00Z'
labels:
  - arkitektur
  - dataläckage
  - träning
dependencies: []
references:
  - dataset
modified_files:
  - xray_detector/infrastructure/dataset_store/export.py
  - xray_detector/application/dataset_service.py
  - xray_detector/ui/training_view.py
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
- [x] #1 export_yolo() delar upp bilderna i train- och val-uppsättningar (default 80/20, seedat och reproducerbart)
- [x] #2 bilder med samma group-id hamnar alltid i samma delmängd (train eller val)
- [x] #3 data.yaml pekar ut train: och val: på olika kataloger
- [x] #4 träningsvyn visar fördelningen (antal train/val-bilder) innan start
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
export_yolo delar upp bilder i images/train och images/val med seedad (42) 80/20-split per capture-grupp, sa valSter- och hogerbild fran samta fingst aldrig hamnar pa olika sidor. data.yaml pekar ut train: images/train och val: images/val (fallback till train om val tomt vid ensam grupp). Manifestet far num_train/num_val och tranningsvyn visar Train/val-redovisning i versioninformationen fore start. Verifierat headlost: 6 grupper -> 10/1, grupper odelade over split, reproducibart.
<!-- SECTION:FINAL_SUMMARY:END -->
