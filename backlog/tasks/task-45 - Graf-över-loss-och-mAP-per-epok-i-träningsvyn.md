---
id: TASK-45
title: Träning - Graf över loss och mAP per epok i träningsvyn
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T11:51:00Z'
updated_date: '2026-11-12T09:53:00Z'
labels: []
dependencies:
  - TASK-44
references:
  - xray_detector/ui/training_view.py
modified_files:
  - README.md
  - xray_detector/ui/training_chart.py
  - xray_detector/ui/training_view.py
  - tests/test_training_chart.py
priority: medium
type: feature
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När epokvisa värden finns (TASK-44) behöver de visas överskådligt. I dag finns ingen graf i träningsvyn; användaren ser bara textrader i loggen. En graf ska visa train- och val-loss samt mAP50 och mAP50-95 över epokerna och uppdateras medan träningen körs, så att överträning och avstannad utveckling syns direkt.

PySide6 6.12 med QtCharts finns redan i projektets venv, så grafen kan byggas utan ny tung dependency. Den ska hantera pågående och avbruten träning samt en kort körning med få epoker.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Träningsvyn visar en graf med loss för train och val per epok
- [x] #2 Grafen visar mAP50 och mAP50-95 per epok
- [x] #3 Grafen uppdateras när ett nytt epokevent kommer
- [x] #4 Axlar och legend är läsbara och anger epok respektive värde
- [x] #5 Grafen visar data även efter avbruten träning
- [x] #6 En körning med en enda epok ger en läsbar graf
- [x] #7 Ingen ny tung dependency krävs
- [x] #8 Tester täcker att serierna får rätt punkter
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
1. ui/training_chart.py: TrainingChart med två QtCharts-grafer, en för train/val-loss och en för mAP50/mAP50-95, med epok på x-axeln och markörer så en enstaka epok syns.
2. Träningsvyn lägger grafen ovanför loggen, rensar den vid start och fyller på den från epoch_metrics-signalen.
3. Axlarna anpassas efter punkterna med ett minsta intervall, så en körning med en epok blir läsbar.
4. Tester läser seriernas punkter och axelintervallen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TrainingChart ritar två QtCharts-grafer: train/val-loss och mAP50/mAP50-95, med epok på x-axeln, axeltitlar och legend under grafen. Träningsvyn rensar grafen vid start och fyller på den från epoch_metrics. Axlarna anpassas efter punkterna med ett minsta intervall, så en enstaka epok syns som en markör. Verifierat med en renderad skärmbild av träningsvyn med åtta epoker: båda graferna visar rätt serier, axlar och legend.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TrainingChart ritar två QtCharts-grafer i träningsvyn: train- och val-loss i den ena och mAP50 och mAP50-95 i den andra, med epok på x-axeln, axeltitlar och legend under grafen. Serierna fylls på från epoch_metrics-signalen och behåller sina punkter när träningen avbryts. Axlarna anpassas efter punkterna med ett minsta intervall och punkterna ritas som markörer, så en körning med en enda epok blir läsbar. QtCharts följer med PySide6, så ingen ny dependency behövs.

Verifierat med en renderad skärmbild av träningsvyn med åtta epoker: båda graferna visar rätt serier, axlar och legend. Enhetstester läser seriernas punkter, axelintervallen och att modulen bara importerar PySide6 och projektet.
<!-- SECTION:FINAL_SUMMARY:END -->
