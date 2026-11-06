---
id: TASK-2
title: Registrera nytränade modeller med manifest i modellväljaren
status: To Do
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - träning
  - detektion
  - arkitektur
dependencies: []
references:
  - trainer
  - detectors
  - detection-view
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Efter en lyckad träning syns resultatet inte i GUI:t: vikterna hamnar under models/v-version/ men detektionsvyns modellväljare listar bara statiska MODEL_SPECS.

Andra brancher (opencode-bigpickle, opencode-deepseek-flash) kopierar best.pt till modellkatalogen tillsammans med ett manifest (training_manifest.json/meta.json: klassnamn, datasetversion, epochs, metrics) och fyller modellväljaren automatiskt när träningen är klar. Se jämförelse_argon.md avsnitt 2:2.

I vibe-glm53: upptäck tränade vikter i models/ (detection/registry.py: MODEL_SPECS plus dynamiskt skannade manifest), skriv manifestet när träningen avslutas, och låt detection_view.py + training_view.py lista de nya modellerna.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 efter en lyckad träning finns vikten i models/ med ett manifest (klasser, datasetversion, datum, metrics)
- [ ] #2 detektionsvynns modellväljare listar nytränade modeller efter träning utan omstart
- [ ] #3 deten slotter fungerar med tränad modell och rätt klassnamn
<!-- AC:END -->
