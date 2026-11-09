---
id: TASK-19
title: Återanslutningsknapp direkt i strömpanelen
status: Done
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T13:38:00Z'
labels:
  - video
  - gui
  - ux
dependencies: []
references:
  - detection-view
  - video-capture
modified_files:
  - xray_detector/ui/detection_view.py
  - tests/test_reconnect.py
priority: medium
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
- [x] #1 tappad källa visar tydlig statusruta med försöksräknare i panelen
- [x] #2 knappen Försök igen återstartar källan utan att öppna meny
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
StreamPanel far en overlagring vid tappad kalla: de tva forsta forso sker automatiskt (statusrad visar 'Ansluter - forso X/3', 1,5 s mellan), vid tredje forso visas knappen 'Forso igen' som aterstartar senaste kallval (typ + index eller filmsvag) direkt via samma signalvag som normalt kallval, utan att kallmenyn oppnas. Inkommande ramar nollstaller forsningsraknaren och doljer overlagringen. Verifierat med 5 nya tester: automatiskt aterforso emitterar kallval, knappen visas efter 3 forso och aterstartar, inkommande ram nollstaller, utan aktiv kalla stannar meddelandet, och DetectionView dirigerar source_lost till ratt panel. Hel svit: 82 tester passerar.
<!-- SECTION:FINAL_SUMMARY:END -->
