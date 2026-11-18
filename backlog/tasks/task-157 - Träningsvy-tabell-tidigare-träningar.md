---
id: TASK-157
title: Träningsvy - tabell tidigare träningar
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-18T12:04:00Z'
updated_date: '2026-11-18T12:23:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 153000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
* Byt namn på kolumn "Körning" till "Datum" och formattera innehållet som vanligt datum och tid.
* Byt namn på kolumn "Basmodell" till "Checkpoint".
* Lägg in kolumn "Modellnamn" som andra kolumn mellan "Datum" och "Checkpoint".
* Byt namn på kolumnerna "Dom" och "Status" till "Status" och "Notering". Välj vilken av de nuvarande kolumnerna som passar bäst till respektive ny rubrik (tycker innehållet är ganska likt).
* Uppdatera även statusraden under tabellen och eventuella referenser i kod/dokumentation med de nya begreppen.
<!-- SECTION:DESCRIPTION:END -->

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
1. Lägg till started_text (lokalt 'YYYY-MM-DD HH:MM') och model_name (namn, annars '-') på TrainingRun.
2. Byt kolumnlistan i ui/training_history.py till Datum, Modellnamn, Checkpoint, Epoker, Tid, mAP50-95, Status, Notering; Status = status_label, Notering = verdict.label.
3. Byt 'Basmodell:' mot 'Checkpoint:' och 'Dom:' mot 'Notering:' i radan under tabellen.
4. Uppdatera testerna (kolumnindex, kolumnnamn) och docs/beteende.md.
<!-- SECTION:PLAN:END -->
