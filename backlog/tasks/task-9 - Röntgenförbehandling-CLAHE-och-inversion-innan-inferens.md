---
id: TASK-9
title: 'Röntgenförbehandling: CLAHE och inversion innan inferens'
status: To Do
assignee: []
created_date: '2026-11-06T14:05:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - detektion
  - röntgen
  - bildbehandling
dependencies: []
references:
  - detectors
  - settings-theme
priority: medium
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Endast vscode-qwen38 har röntgenspecifik förbehandling (xray_detector/detection/preprocess.py): CLAHE-kontrastförstärkning i LAB-färgrymd som bevarar dual-energy-pseudofärger, samt invertering av mörka röntgenbilder, konfigurerbart per källa. Se jämförelse_glm53.md punkt 4 och jämförelse_argon.md avsnitt 7:1.

Lägg preprocess()-stege in i detektorregistret (före detect()), med per-ström- eller global inställning i GUI:t (Inställningar: Ingen/CLAHE/Invertera/Auto).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 förbehandling kan väljas (av/CLAHE/invert) och appliceras på ramar före detektion
- [ ] #2 CLAHE appliceras på ljuskanalen i LAB så att färg kanter bevaras
<!-- AC:END -->
