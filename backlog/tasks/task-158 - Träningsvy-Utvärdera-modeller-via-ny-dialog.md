---
id: TASK-158
title: Träningsvy - Utvärdera modeller via ny dialog
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-18T12:21:00Z'
updated_date: '2026-11-18T12:37:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 154000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu finns en liten sektion under tidigare träningar att man kan utvärdera modeller. Jag vill utveckla den funktionen mycket och tänker att det är bäst att göra det i en ny dialog som öppnas via knapp under tidigare träningar. Flytta in eventuell befintlig utvärderingsfunktionalitet till den nya dialogen.

Jag tänker mig att man inför en checkbox först i varje rad i tabellen över tidigare träningar samt en toggle markera/avmarkera alla. Knappen "Utvärdera" gör en jämförelse av de valda modellerna och visualiserar det i den dialog som öppnas. Det kan vara en sammanfattande tabell samt utvalda relevanta grafer för t ex uppmätt detektionsförmåga.

Som grund till uppmätt detektionsförmåga kan en vi t ex använda:
1) ett separat dataset med bilder och annoteringar vilket ger både träffsäkerhet och eventuella falska identifieringar
2) en katalog med bilder utan annoteringar, där kan uppmätingen endast räkna antal detektioner
3) en videofil med bilder utan annoteringar och där med samma resultat som punkt 2

Finns det andra sätt att lösa det eller andra relevanta metrics för utvärdering är jag öppen för förslag
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
1. metrics.py: track_lengths() och stability_summary() för spårlängder mellan bildrutor (ren numpy, testbar).
2. evaluation.py: EvaluationSource (dataset/mapp/video), bildruteströmmar per källtyp, evaluate_detections() för källor utan annoteringar (detektioner/bild, per klass, andel bilder med träff, medelkonfidens, konfidenshistogram, stabilitet), evaluate_source() och compare_runs().
3. ui/evaluation_chart.py: BarChart med grupperade staplar, ritad med QPainter och palettfärger som LineChart.
4. ui/evaluation_dialog.py: EvaluationDialog med källväljare (dataset + delmängd, bildmapp, videofil), sammanfattningstabell, grafer och bakgrundskörning.
5. ui/training_history.py: kryssruta först i varje rad, 'Markera alla', knappen 'Utvärdera valda...' som öppnar dialogen. Den infogade delmängdslistan, utvärderingsknappen och körningen flyttas till dialogen; etiketten med sparad utvärdering blir kvar som information.
6. Tester för metrics, källtyper, dialog och historikvyns kryssrutor. docs/beteende.md uppdateras.
<!-- SECTION:PLAN:END -->
