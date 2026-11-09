---
id: TASK-4
title: Bygg testsvit (enhet + GUI-smoke utan hårdvara)
status: In Progress
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T09:24:00Z'
labels:
  - test
  - kvalitet
dependencies: []
references:
  - dataset
  - annotation-view
  - video-capture
priority: high
type: task
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vibe-glm53 har helt saknar tester (tom tests/unit). Bäst testsvit finns i opencode-deepseek-flash (8 testfiler: coco, export, geometri, config, pending, träning, annotering-GUI) och opencode-bigpickle (enhet + pytest-qt UI-smoke med FakeDetector och syntetisk videosource, QT_QPA_PLATFORM=offscreen).

Se jämförelse_glm53.md punkt 2 och jämförelse_qwen38.md.

Prioritera: dataset-lagret (store/export/delete_images, capture-group), capture (source pacing, UVC-fallback-logik), annoteringscanvas (rita/flytta/resize/delete), GUI-smoke (stack MainWindow -> fånga -> annotera -> spara) med FakeDetector.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pytest kan köras utan kameror/GPU (FakeDetector + syntetisk data)
- [ ] #2 datasetlagret: add_samples/delete_images/export (inkl. split) har enhetstester
- [ ] #3 ett GUI-smoketest täcker fånga -> annotera -> spara-flödet
<!-- AC:END -->
