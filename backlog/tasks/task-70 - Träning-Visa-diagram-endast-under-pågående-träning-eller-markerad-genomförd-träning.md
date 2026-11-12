---
id: TASK-70
title: >-
  Träning - Visa diagram endast under pågående träning eller markerad genomförd
  träning
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T17:17:00Z'
updated_date: '2026-11-12T17:28:00Z'
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
- [x] #1 Diagramytorna är dolda när ingen träning pågår och ingen tidigare träning är vald
- [x] #2 Diagrammen visas med livedata när en träning har startats
- [x] #3 När en genomförd träning markeras i listan visas dess sparade epokvärden i diagrammen
- [x] #4 När markeringen tas bort och ingen träning pågår döljs diagrammen igen
- [x] #5 Testerna för träningsvyn, grafen och epokvärdena passerar
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
1. read_epoch_history i infrastructure/training/epoch_metrics.py läser hela metrics-filen (results.csv för YOLO, metrics.csv för RF-DETR) till EpochMetrics per epok.
2. run_epochs(run) i application/training_history.py pekar ut filen för en TrainingRun.
3. TrainingChart.has_data() svarar på om någon serie har punkter.
4. TrainingHistoryView får signalen run_selected som bara sänds när valet faktiskt ändras, så en refresh inte släcker grafen.
5. TrainingView: grafen dold vid start, synlig när träning startats, laddar vald körnings sparade epoker, dold igen när valet tas bort och ingen träning pågår.
6. Tester för läsning av epokhistorik, val i listan och synligheten; README uppdateras.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
read_epoch_history i epoch_metrics.py läser hela metrics-filen från början med MetricsTail + EpochAccumulator, så RF-DETR:s två rader per epok slås ihop som under träningen. run_epochs(run) i application/training_history.py pekar ut yolo/results.csv eller rfdetr/metrics.csv. TrainingChart.has_data() styr synligheten tillsammans med _training_active(). TrainingHistoryView.run_selected sänds bara när valet faktiskt ändras, så en refresh efter avslutad träning inte släcker grafen. Verifierat med uv run pytest: 469 passed, 1 skipped. Nya tester täcker läsning av YOLO- och RF-DETR-historik, val i listan, borttaget val, val under pågående träning och att grafen behåller livedata efter avslut.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Diagramytorna i träningsvyn är dolda tills det finns något att visa. De visas när en träning startas och fylls med livedata som förut. Markeras en genomförd träning i Tidigare träningar laddas dess sparade epokvärden ur körningens results.csv (YOLO) eller metrics.csv (RF-DETR) och ritas i graferna; manifestet räcker inte eftersom det bara sparar sista epoken. Tas markeringen bort döljs graferna igen, och en ny träning släpper ett gammalt val så livedata tar över. Verifierat med hela testsviten: 469 passed, 1 skipped. Kvar att göra manuellt: en riktig träning med GUI:t för att se övergången live, eftersom testerna använder en worker utan process.
<!-- SECTION:FINAL_SUMMARY:END -->
