---
id: TASK-53
title: Välj vilka klasser som ska detekteras, per modell
status: To Do
assignee: []
created_date: '2026-11-11T12:49:00Z'
labels: []
dependencies:
  - TASK-52
references:
  - xray_detector/ui/detection_view.py
  - xray_detector/infrastructure/detectors/base.py
priority: high
type: feature
ordinal: 51000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
En modell kan detektera många klasser (yolo26n är tränad på 80 COCO-klasser) och användaren vill bara se en delmängd av dem. I dag finns ingen filtrering: allt modellen hittar ritas i overlayen. Klasslistan skiljer sig mellan modeller, så inställningarna kan inte vara en fast lista — de måste följa vald modell. Alla klasser ska vara påslagna från början så att beteendet är oförändrat tills användaren aktivt klickar bort något. Bygger på att detektorn exponerar modellens klassnamn (TASK-52).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Detektionsinställningarna listar alla klasser som vald modell kan detektera
- [ ] #2 Alla klasser är valda när en modell laddas första gången
- [ ] #3 Bortvalda klasser ger inga detektioner i overlayen
- [ ] #4 Klasslistan i inställningarna uppdateras när användaren byter modell
- [ ] #5 Valen sparas per modell så att de finns kvar när man byter tillbaka
- [ ] #6 Klasser som tillkommer i en modell visas som valda
- [ ] #7 Om alla klasser väljs bort visas ett tydligt meddelande och ingen detektion körs
- [ ] #8 Tester täcker filtrering, modellbyte och persistens
- [ ] #9 README beskriver klassfiltret
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
