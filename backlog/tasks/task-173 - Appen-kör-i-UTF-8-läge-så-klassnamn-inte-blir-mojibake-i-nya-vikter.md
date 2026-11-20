---
id: TASK-173
title: Appen kör i UTF-8-läge så klassnamn inte blir mojibake i nya vikter
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-20T21:02:00Z'
updated_date: '2026-11-20T21:02:00Z'
labels: []
dependencies: []
type: bug
ordinal: 465000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Mojibaken i RF-DETR-vikterna uppstår vid träningen: pycocotools läser _annotations.coco.json med open(path, 'r') utan encoding, alltså cp1252 på Windows, så 'löpare' blir 'lÃ¶pare' i model.class_names och i checkpointen. TASK-172 rättade symptomet i detektorn. Den här uppgiften tar bort orsaken: PYTHONUTF8=1 ska gälla för hela appen och för processerna den startar. Flaggan läses när tolken startar och kan inte slås på under körning, så appen måste sätta den i miljön och starta om sig själv en gång när läget är av. Träningsprocessen startas som en QProcess och ärver appens miljö.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Appen startar i UTF-8-läge även när den startats utan PYTHONUTF8
- [ ] #2 Träningsprocessen (QProcess) ärver flaggan och får utf8_mode=1
- [ ] #3 Omstarten sker högst en gång, även om kommandoraden innehåller -X utf8=0
- [ ] #4 Tester täcker flaggan, omstarten, enkelheten och barnprocessen
- [ ] #5 Hela testsviten passerar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Sätt PYTHONUTF8=1 i appens miljö och starta om processen en gång när UTF-8-läget är av, så hela appen och barnprocesserna läser text som UTF-8.
2. Låt en markör i miljön se till att omstarten sker högst en gång, så en kommandorad med -X utf8=0 inte kan ge en oändlig omstart.
3. Tester: flaggan sätts, ingen omstart i UTF-8-läge, omstarten återanvänder kommandoraden, högst en omstart, och en QProcess-barnprocess ärver flaggan.
4. Kör ruff och hela testsviten.
5. Verifiera att appen startar och att träningsprocessen får utf8_mode=1.
<!-- SECTION:PLAN:END -->
