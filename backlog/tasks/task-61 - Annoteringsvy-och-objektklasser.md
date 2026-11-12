---
id: TASK-61
title: Annoteringsvy och objektklasser
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T09:11:00Z'
updated_date: '2026-11-12T09:22:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/application/dataset_service.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/main_window.py
  - tests/test_annotation_classes.py
  - tests/test_export_split.py
  - tests/test_rfdetr.py
  - README.md
type: enhancement
ordinal: 59000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu visas fyra förvalda objektklasser i annoteringsvyn, men det behöver ändras så att det default är de klasser som vald modell har som läggs in istället för de fasta.

Möjlighet att lägga till och ta bort klasser ska finnas kvar. Tillagda klasser utöver default läggs in i det dataset som applikationen har. Dataset i applikationen är alltså master. Modellens klasser lägger bara in defaultvärden.

Fråga om det behövs förtydliganden.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Annoteringsvyns klasslista fylls med vald modells klasser när datasetet är tomt
- [x] #2 Datasetets klasser är master och visas i stället för modellens när datasetet har klasser
- [x] #3 Klasser som läggs till i annoteringsvyn skrivs till datasetet
- [x] #4 Klasser som tas bort försvinner ur datasetet; en klass som används av sparade annoteringar kan inte tas bort
- [x] #5 Klasslistan sparas inte längre i QSettings utan följer datasetet
- [x] #6 Tester täcker standardvärden, datasetet som master och tillägg/borttagning
- [x] #7 README beskriver att datasetet är master för klasslistan
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
1. DatasetStore/DatasetService: klasslistan är datasetets kategorier — classes(), set_classes() och class_in_use(); en ny kategori får ett ledigt id så id:n inte krockar efter en borttagning.
2. AnnotationView: klasslistan byggs ur datasetet. Är datasetet tomt används vald modells klasser som standardvärden och skrivs in i datasetet när vyn öppnas. Lägg till/ta bort skriver till datasetet; en klass som används av sparade annoteringar kan inte tas bort.
3. DetectionView exponerar model_class_names(); MainWindow skickar den som standardklasskälla till annoteringsvyn.
4. Tester för standardvärden från modellen, datasetet som master, tillägg/borttagning, id-bevaring och att osparade klasser inte längre ligger i QSettings.
5. README: annoteringsvyns klasslista och config.yaml classes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Klasslistan i annoteringsvyn är nu datasetets kategorier i dataset.json. DatasetStore/DatasetService har fått classes(), set_classes(), class_in_use() och has_dataset(); set_classes behåller id:t för namn som finns kvar, och _category_id tar max(id)+1 så en ny klass inte återanvänder ett id efter en borttagning. AnnotationView.refresh_classes() bygger combon ur datasetet; är datasetet tomt och dataset.json ännu inte skrivet används vald modells klasser (DetectionView.model_class_names(), skickad från MainWindow) och de skrivs in i datasetet när vyn öppnas. config.classes är kvar som reservlista innan modellen är laddad och för overlayfärgerna. Lägg till/ta bort skriver till datasetet i stället för QSettings (annotation/classes skrivs inte längre); en klass som sparade annoteringar refererar kan inte tas bort, och tas alla klasser bort ligger listan kvar tom. Verifierat: uv run pytest -q gav 329 passed, 1 skipped (14 nya tester i tests/test_annotation_classes.py), och en manuell körning genom MainWindow med en tvåklassdetektor visade modellens klasser vid öppning, tillägg/borttagning i datasetet och att ett nytt fönster med samma dataset behåller datasetets klasser.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Annoteringsvyns klasslista är nu datasetets egna klasser i dataset.json i stället för fyra fasta. När datasetet är tomt fylls listan med vald modells klasser (DetectionView.model_class_names()) och de skrivs in i datasetet första gången vyn öppnas; därefter är datasetet master och modellens klasser används inte igen. Klasser som läggs till eller tas bort skrivs direkt till datasetet i stället för QSettings, och en klass som sparade annoteringar refererar kan inte tas bort. DatasetStore.set_classes behåller id:n för namn som finns kvar och en ny kategori får max(id)+1, så id:n inte krockar efter en borttagning. config.classes är kvar som reservlista innan modellen är laddad och för overlayfärgerna. Verifierat med 329 gröna tester (14 nya i tests/test_annotation_classes.py) och en manuell körning genom MainWindow med en tvåklassdetektor: modellens klasser vid öppning, tillägg/borttagning i datasetet och datasetets klasser kvar i ett nytt fönster. Kvar att känna till: ett dataset som sparades före ändringen behåller sina fyra klasser eftersom datasetet är master.
<!-- SECTION:FINAL_SUMMARY:END -->
