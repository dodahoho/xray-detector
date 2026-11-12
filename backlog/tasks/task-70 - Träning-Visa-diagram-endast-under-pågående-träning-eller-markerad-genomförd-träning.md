---
id: TASK-70
title: >-
  Träning - Visa diagram endast under pågående träning eller markerad genomförd
  träning
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-12T17:17:00Z'
updated_date: '2026-11-12T17:22:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 68000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu är diagramytorna synliga även när träning inte startats eller någon tidigare genomförd träning är vald.

Visa diagrammen med livedata när träning startats.

Visa även diagrammen när en redan genomförd träning markeras och visa då dess sparade data i diagrammen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Diagramytorna är dolda när ingen träning pågår och ingen tidigare träning är vald
- [ ] #2 Diagrammen visas med livedata när en träning har startats
- [ ] #3 När en genomförd träning markeras i listan visas dess sparade epokvärden i diagrammen
- [ ] #4 När markeringen tas bort och ingen träning pågår döljs diagrammen igen
- [ ] #5 Testerna för träningsvyn, grafen och epokvärdena passerar
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
1. read_epoch_history i infrastructure/training/epoch_metrics.py läser hela metrics-filen (results.csv för YOLO, metrics.csv för RF-DETR) till EpochMetrics per epok.
2. run_epochs(run) i application/training_history.py pekar ut filen för en TrainingRun.
3. TrainingChart.has_data() svarar på om någon serie har punkter.
4. TrainingHistoryView får signalen run_selected som bara sänds när valet faktiskt ändras, så en refresh inte släcker grafen.
5. TrainingView: grafen dold vid start, synlig när träning startats, laddar vald körnings sparade epoker, dold igen när valet tas bort och ingen träning pågår.
6. Tester för läsning av epokhistorik, val i listan och synligheten; README uppdateras.
<!-- SECTION:PLAN:END -->
