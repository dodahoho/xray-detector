---
id: TASK-58
title: Export av dataset till COCO och YOLO tillhör fliken dataset, inte träning
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T21:50:00Z'
updated_date: '2026-11-11T22:04:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 56000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Just nu ligger knappar för att exportera dataset under fliken träning. Det ska istället ligga under fliken dataset.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Exportknapparna för COCO och YOLO ligger i datasetvyn, inte i träningsvyn
- [x] #2 Exporten körs i bakgrunden med upptagenindikatorn och rapporterar resultatet i statusraden, som förut
- [x] #3 Genvägarna Alt+E och Alt+Y fungerar i datasetvyn och krockar inte med flikradens mnemonik
- [x] #4 Träningsvyn exporterar fortfarande YOLO/RF-DETR automatiskt när träningen startar
- [x] #5 Alla tester passerar och README samt groma-arkitekturen beskriver den nya placeringen
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
1. Flytta exportknapparna och exportlogiken från TrainingView till DatasetView; DatasetView tar emot AppConfig för export_dir.
2. Låt datasetvyns upptagenindikator hanteras av både omladdning och export, så den stängs först när ingen uppgift är kvar.
3. Uppdatera MainWindow (wait_for_export) och testerna för datasetvyn, genvägarna och upptagenindikatorn.
4. Uppdatera README (lägen, tangentbord) och groma-komponenterna dataset-view/training-view.
5. Kör testsviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Flyttade exportknapparna (COCO/YOLO) och hela exportlogiken från TrainingView till DatasetView. DatasetView tar nu emot AppConfig för att komma åt export_dir, samma signaturmönster som de andra vyerna. Datasetvyns upptagenindikator delas av omladdning och export: _update_busy() stänger den först när ingen av uppgifterna är kvar, och refresh() rör inte en indikator som en pågående export äger. MainWindow väntar in datasetvyns export vid stängning. TrainingView har kvar sin automatiska export vid träningsstart (YOLO/RF-DETR) men är av med exportknapparna, BackgroundTask-beroendet och den nu oanvända BusyIndicator-instansen.

Tester: DatasetView-konstruktionerna i dataset-, sorterings-, urvals- och busy-testerna uppdaterade; gemensam config-fixture i tests/conftest.py ersätter tre identiska lokala kopior. Nya tester: exportknapparna ligger i datasetvyn och inte i träningsvyn (test_gui_smoke.py) samt att indikatorn hålls tänd när export och omladdning överlappar (test_busy_operations.py). Hela sviten: 279 passed, 1 skipped.

Dokumentation: README (lägen, tidskrävande operationer, tangentbordstabellen) samt groma-komponenterna dataset-view och training-view uppdaterade via groma CLI. Kvarstår: groma tillåter inte att aktuella relationer tas bort, så training-view.md behåller raderna mot busy_indicator.py och background_task.py trots att träningsvyn inte längre importerar dem.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Exportknapparna för COCO och YOLO flyttade från träningsvyn till datasetvyn. DatasetView tar nu emot AppConfig (samma mönster som de andra vyerna) och äger exportknapparna, bakgrundsjobbet via BackgroundTask och upptagenindikatorn. Eftersom datasetvyn redan använder indikatorn för omladdningen delar de på den: _update_busy() stänger den först när ingen uppgift är kvar, och en pågående export behåller sin text. MainWindow väntar in datasetvyns export vid stängning. TrainingView behåller den automatiska exporten när träningen startar men är av med knapparna, BackgroundTask-beroendet och den nu oanvända BusyIndicator-instansen.

Verifiering: hela sviten 279 passed, 1 skipped. Nya tester täcker att knapparna ligger i datasetvyn och inte i träningsvyn (test_gui_smoke.py), att indikatorn hålls tänd när export och omladdning överlappar (test_busy_operations.py) och att träningsstarten fortfarande skriver exports/yolo/data.yaml (test_model_layout.py). Genvägarna Alt+E och Alt+Y kontrolleras av test_shortcuts.py, inklusive att mnemoniken är unik per vy och skild från flikraden.

Dokumentation: README (lägen, tidskrävande operationer, tangentbordstabellen) och groma-komponenterna dataset-view/training-view uppdaterade via groma CLI. Kvarstår: groma tillåter inte att aktuella relationer tas bort, så training-view.md behåller raderna mot busy_indicator.py och background_task.py trots att träningsvyn inte längre importerar dem.
<!-- SECTION:FINAL_SUMMARY:END -->
