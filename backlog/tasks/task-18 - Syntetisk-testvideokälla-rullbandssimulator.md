---
id: TASK-18
title: Syntetisk testvideokälla (rullbandssimulator)
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - video
  - test
  - demo
dependencies: []
references:
  - video-capture
  - detection-view
priority: low
type: feature
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
antigravity har en inbyggd syntetisk dual-energy röntgensimulator (animerat rullband med väskor, metall och batterier) och opencode-bigpickle har en test-pattern-källa per kamera, så hela appen kan köras och demoas utan fysiska UVC-kort. Se jämförelse_argon.md avsnitt 5:2.

Lägg till en SimpleSource/PatternSource i xray_detector/capture/source.py (rullande bilder eller animerad syntetisk ström) och en post i källmenyn, mycket användbar för tester och demo, kombinera gärna med testsvit-uppgiften.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 källmenyn erbjuder en syntetisk röntgenström utan kameror
- [ ] #2 FakeDetector/testsvit kan köra mot den nya källan
<!-- AC:END -->
