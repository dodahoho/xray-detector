---
id: TASK-19
title: Återanslutningsknapp direkt i strömpanelen
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - video
  - gui
  - ux
dependencies: []
references:
  - detection-view
  - video-capture
priority: low
type: enhancement
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vscode-qwen38 har per-panel fel-UI: statusoverlay med anslutningsförsök och en knapp Försök igen direkt i kameravyn, mycket tydligt när ett USB3-kort tappat kontakten. Se jämförelse_argon.md avsnitt 7:3.

I vibe-glm53: visa overlay i StreamPanel när källan tappas (idag bara texten Ingen videokälla) med knapp som återstartar senaste källval.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tappad källa visar tydlig statusruta med försöksräknare i panelen
- [ ] #2 knappen Försök igen återstartar källan utan att öppna meny
<!-- AC:END -->
