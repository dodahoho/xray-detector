---
id: TASK-59
title: Träningsvy - Lista tidigare träningar och exportera modell
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T09:01:00Z'
updated_date: '2026-11-12T10:07:00Z'
labels: []
dependencies: []
modified_files:
  - README.md
  - xray_detector/application/training_history.py
  - xray_detector/ui/training_history.py
  - xray_detector/ui/training_view.py
  - tests/test_training_history.py
type: feature
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Man behöver kunna lista tidigare genomförda träningar, se tidsåtgång och viktiga parametrar

Det måste även gå att exportera utvalda egentränade modeller i lämpligt format
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Träningsvyn listar tidigare träningar med körning, basmodell, familj, antal epoker, tidsåtgång och status
- [x] #2 Listan visar viktiga parametrar för vald körning: dataset, bildstorlek, batch och mAP50-95
- [x] #3 Listan uppdateras när en träning avslutas
- [x] #4 En vald modell kan exporteras till en katalog användaren väljer
- [x] #5 Exporten skriver modellvikterna och manifestet så modellen kan användas utanför appen
- [x] #6 Exportknappen är avstängd när ingen körning är vald
- [x] #7 Tester täcker listning, tidsåtgång och export
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
1. application/training_history.py: TrainingRun läser training_manifest.json under models/trained/, nyast först, med tidsåtgång ur duration_seconds eller started/finished. export_run kopierar vikterna och manifestet till en vald katalog.
2. ui/training_history.py: tabell med körning, basmodell, epoker, tid, mAP50-95 och status, en detaljrad för vald körning och en Exportera modell-knapp som är avstängd utan val.
3. Träningsvyn lägger loggen och tidigare träningar i en flikwidget under grafen och uppdaterar listan när en träning avslutas.
4. Tester för listning, sortering, tidsåtgång, exportinnehåll och knapptillstånd.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tidigare träningar läses ur training_manifest.json under models/trained/ och listas nyast först med körning, basmodell, epoker (körda/planerade vid avbrott), tidsåtgång, mAP50-95 och status. Tidsåtgången tas ur duration_seconds och räknas annars ut ur started/finished. Raden under listan visar vald körnings parametrar. Exportera modell kopierar vikterna och manifestet till en vald katalog; knappen är avstängd utan val. Loggen och listan ligger i var sin flik under grafen, och listan uppdateras när en träning avslutas. Verifierat med de riktiga körningarna i tempkatalogen: 12 körningar listades nyast först och exporten skrev best.pt (5,4 MB) och training_manifest.json till exportkatalogen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningsvyn har en flik Tidigare träningar under grafen, vid sidan av Logg. Listan läses ur training_manifest.json under models/trained/ och visar körning, basmodell, epoker (körda/planerade när körningen avbröts), tidsåtgång, mAP50-95 och status, nyast först. Tidsåtgången tas ur duration_seconds och räknas annars ut ur started/finished. Raden under listan visar vald körnings parametrar: familj, basmodell, dataset, bildstorlek, batch, epoker, mAP50-95, status och klasser. Listan uppdateras när en träning avslutas.

Exportera modell kopierar vald körnings vikter och manifest till en katalog användaren väljer, så modellen kan användas utanför appen. Vikterna behåller sitt format (.pt för YOLO, .pth för RF-DETR), vilket är det både appen och ultralytics/rfdetr läser. Knappen är avstängd tills en körning är vald.

Verifierat med de riktiga körningarna i tempkatalogen: 12 körningar listades nyast först med rätt tidsåtgång och status, och exporten skrev best.pt (5,4 MB) och training_manifest.json till exportkatalogen. En renderad skärmbild av vyn visar tabellen, detaljraden och exportknappen.
<!-- SECTION:FINAL_SUMMARY:END -->
