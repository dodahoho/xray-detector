---
id: TASK-20
title: Separat modellval per videoström
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - detektion
  - gui
dependencies: []
references:
  - detection-view
  - detectors
priority: low
type: feature
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vscode-qwen38 tillåter olika modell per kameraström (model_left och model_right), användbart när de två vyerna visar olika vinklar eller energi och därmed har separata tränade modeller. Se jämförelse_argon.md avsnitt 7:2.

I vibe-glm53 delar båda strömmarna samma detektorinstans. Utöka detektionsvyn med modellval per panel och bygg en detektorinstans per ström i CameraService (worker.set_detector redan per ström; detektorn byggs bara per modellbygge i _on_model_changed idag).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 varje ström kan använda egen modell/tröskel
- [ ] #2 modellval per ström persistas i QSettings
<!-- AC:END -->
