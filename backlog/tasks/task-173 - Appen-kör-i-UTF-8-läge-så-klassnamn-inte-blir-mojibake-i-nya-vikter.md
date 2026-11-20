---
id: TASK-173
title: Appen kör i UTF-8-läge så klassnamn inte blir mojibake i nya vikter
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-20T21:02:00Z'
updated_date: '2026-11-20T21:10:00Z'
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
- [x] #1 Appen startar i UTF-8-läge även när den startats utan PYTHONUTF8
- [x] #2 Träningsprocessen (QProcess) ärver flaggan och får utf8_mode=1
- [x] #3 Omstarten sker högst en gång, även om kommandoraden innehåller -X utf8=0
- [x] #4 Tester täcker flaggan, omstarten, enkelheten och barnprocessen
- [x] #5 Hela testsviten passerar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Sätt PYTHONUTF8=1 i appens miljö och starta om processen en gång när UTF-8-läget är av, så hela appen och barnprocesserna läser text som UTF-8.
2. Låt en markör i miljön se till att omstarten sker högst en gång, så en kommandorad med -X utf8=0 inte kan ge en oändlig omstart.
3. Tester: flaggan sätts, ingen omstart i UTF-8-läge, omstarten återanvänder kommandoraden, högst en omstart, och en QProcess-barnprocess ärver flaggan.
4. Kör ruff och hela testsviten.
5. Verifiera att appen startar och att träningsprocessen får utf8_mode=1.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering: _ensure_utf8_mode ger utf8_mode=1 och preferred=utf-8 efter omstarten (probe mot app.py). En QProcess som startas med flaggan i miljön får utf8_mode=1, alltså ärver träningsprocessen den. python -X utf8=0 startar om en gång och ger sedan upp i stället för att loopa. Appen startar som vanligt: PID 23476 loggade 'Startar X-ray detector' och 'Dataset: 13 bildpar, klasser=[löpare]'. ruff rent, 1036 passed och 1 skipped i hela sviten.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Appen startar nu i UTF-8-läge. app.py:s _ensure_utf8_mode sätter PYTHONUTF8=1 i miljön och startar om processen en gång med samma kommandorad när läget är av, eftersom flaggan läses när tolken startar och inte kan slås på under körning. Träningsprocessen startas som en QProcess och ärver flaggan, så pycocotools läser _annotations.coco.json som UTF-8 och nya RF-DETR-vikter får klassnamnet löpare i stället för lÃ¶pare.

En markör i miljön (XRAY_UTF8_RESTARTED) gör att omstarten sker högst en gång. Utan den skulle en kommandorad med -X utf8=0, som slår miljövariabeln, ge en oändlig omstart.

Verifiering: utf8_mode=1 och preferred=utf-8 efter omstarten; en QProcess-barnprocess får utf8_mode=1; -X utf8=0 startar om en gång och ger sedan upp; appen startar normalt och loggar klasser=[löpare]. ruff rent, 1036 passed och 1 skipped.

Kvarstående: TASK-172:s rättning i detektorn behålls, eftersom de fyra redan tränade snapshotsen bär mojibake i vikterna. Körs train_task direkt från CLI:t måste flaggan sättas i skalet.
<!-- SECTION:FINAL_SUMMARY:END -->
