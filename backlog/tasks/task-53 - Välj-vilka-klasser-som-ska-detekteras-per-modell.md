---
id: TASK-53
title: Detektion - Välj vilka klasser som ska detekteras, per modell
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T12:49:00Z'
updated_date: '2026-11-11T22:33:00Z'
labels: []
dependencies:
  - TASK-52
references:
  - xray_detector/ui/detection_view.py
  - xray_detector/infrastructure/detectors/base.py
modified_files:
  - xray_detector/infrastructure/detectors/base.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - xray_detector/ui/settings_dialog.py
  - xray_detector/ui/detection_view.py
  - tests/test_class_filter.py
  - tests/test_settings_dialog.py
  - tests/test_detector_settings.py
  - tests/test_model_layout.py
  - tests/test_rfdetr.py
  - README.md
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
- [x] #1 Detektionsinställningarna listar alla klasser som vald modell kan detektera
- [x] #2 Alla klasser är valda när en modell laddas första gången
- [x] #3 Bortvalda klasser ger inga detektioner i overlayen
- [x] #4 Klasslistan i inställningarna uppdateras när användaren byter modell
- [x] #5 Valen sparas per modell så att de finns kvar när man byter tillbaka
- [x] #6 Klasser som tillkommer i en modell visas som valda
- [x] #7 Om alla klasser väljs bort visas ett tydligt meddelande och ingen detektion körs
- [x] #8 Tester täcker filtrering, modellbyte och persistens
- [x] #9 README beskriver klassfiltret
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
1. BaseDetector får set_enabled_classes() och filter_detections(); YOLO och RF-DETR filtrerar sina detektioner innan de returneras.
2. ClassFilterSection i settings_dialog.py: en kryssruta per klass som vald modell kan detektera, plus en varning när ingen klass är vald.
3. DetectionView: detektionsvyns inställningsknapp öppnar sektionen, klassnamnen cachas per modell när detektorn laddas, och bortvalda klasser sparas per modell (detection/classes_off/<modellnyckel>). Nya klasser i en modell är därför valda från början.
4. Klassfiltret appliceras när modellen laddas och när ett val ändras; är alla klasser bortvalda kopplas detektorn bort och ett tydligt meddelande visas.
5. Tester för filtrering, modellbyte, persistens och alla-av; README beskriver klassfiltret.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Klassfiltret ligger i detektionsvyns inställningar: en kryssruta per klass som vald modell kan detektera, byggd från modellens klassnamn (TASK-52). Klassnamnen cachas per modellnyckel när detektorn laddas, så listan går att visa även när detektorn är pausad. Bara bortval sparas, som en JSON-lista under detection/classes_off/<modellnyckel>; därför är en klass som tillkommer i en modell vald från början. Filtreringen sitter i BaseDetector.set_enabled_classes()/filter_detections(), som både YoloDetector och RfDetrDetector anropar innan de returnerar, och vyn kopplar om detektorn när valet ändras så utjämningen börjar om. Är alla klasser bortvalda returnerar _active_detector() None, detektorn kopplas bort, overlayn rensas och både sektionen och statusraden visar 'Inga klasser valda – ingen detektion körs'. Dialogen är modal, så klasslistan byggs om varje gång den öppnas och följer då vald modell. Verifierat: uv run pytest -q gav 303 passed, 1 skipped (16 nya tester i tests/test_class_filter.py), och en manuell körning mot den riktiga YOLO26 medium-modellen visade 80 kryssrutor (alla valda), sparat bortval som ["person"], ingen aktiv detektor när alla bockades av och att en klass på igen startade detektionen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Detektionsvyn har fått ett klassfilter per modell. Inställningsknappen (tidigare avstängd) öppnar en sektion med en kryssruta per klass som vald modell kan detektera; alla är valda från början. Bortval sparas per modell under detection/classes_off/<modellnyckel>, vilket gör att en klass som tillkommer i en modell är vald direkt. Filtreringen sker i detektorn (BaseDetector.filter_detections, anropad av både YOLO och RF-DETR), och vyn kopplar om detektorn vid varje ändring. Väljs alla klasser bort kopplas detektorn bort och både sektionen och statusraden visar 'Inga klasser valda – ingen detektion körs'. Verifierat med 303 gröna tester (16 nya) och en manuell körning mot YOLO26 medium med COCO:s 80 klasser. README beskriver filtret och vilka vyer som har egna inställningar.
<!-- SECTION:FINAL_SUMMARY:END -->
