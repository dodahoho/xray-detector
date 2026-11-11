---
id: TASK-48
title: Registrera tränade modeller med rätt familj i modellväljaren
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T11:51:00Z'
updated_date: '2026-11-11T20:31:00Z'
labels: []
dependencies:
  - TASK-47
references:
  - xray_detector/application/model_registry.py
  - xray_detector/ui/detection_view.py
modified_files:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/application/model_registry.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - tests/test_model_layout.py
  - README.md
priority: medium
type: bug
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
trained_models i application/model_registry.py skapar alltid ModelSpec(..., family="yolo", ...), oavsett vad manifestet säger. En RF-DETR-körning registreras därför som YOLO och laddas med YoloDetector, vilket misslyckas när vikterna är en .pth. Det gör RF-DETR-snapshots oanvändbara i modellväljaren, även om TASK-47 sparar dem korrekt.

Manifestet behöver familjen (TASK-47) och trained_models ska använda den. Saknas familj i ett äldre manifest ska beteendet vara bakåtkompatibelt.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Manifestet anger modellfamilj
- [x] #2 trained_models använder manifestets familj i stället för hårdkodad yolo
- [x] #3 En RF-DETR-snapshot laddas med RfDetrDetector i modellväljaren
- [x] #4 En YOLO-snapshot laddas med YoloDetector som förut
- [x] #5 Äldre manifest utan familj fungerar fortfarande
- [x] #6 Tester täcker båda familjerna
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
1. Skriv familj till training_manifest.json i train_task._write_manifest.
2. Läs familjen i trained_models; saknat eller okänt värde faller tillbaka på yolo så äldre manifest fungerar.
3. Låt RfDetrDetector ladda en tränad .pth via rfdetr.from_checkpoint när viktsökvägen är en befintlig fil, annars som förut via storleksnyckeln.
4. Tester: båda familjerna i trained_models, RF-DETR-snapshot ger RfDetrDetector, YOLO-snapshot ger YoloDetector, äldre manifest utan familj.
5. Uppdatera README om modellväljaren.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- train_task._write_manifest skriver family i training_manifest.json.
- model_registry.trained_models läser manifestets family; saknat eller tomt värde faller tillbaka på yolo så äldre manifest fungerar.
- RfDetrDetector tar emot antingen en storleksnyckel (rfdetr-small) eller en sökväg till en sparad viktfil. En fil laddas med rfdetr.from_checkpoint, som läser både arkitektur och antal klasser ur checkpointen; parametern heter nu weights som i YoloDetector.
- create_detector behövde ingen ändring: den skickar redan spec.weights vidare.

Verifiering:
- pytest: 270 passed, 1 skipped (före ändringen 266 passed, 1 skipped).
- ruff check xray_detector tests: 63 fel både före och efter, inga nya i berörda filer.
- Manuell GUI-kontroll med en påhittad RF-DETR-körning under models/trained/v3: posten trained-v3 hamnade i modellväljaren med familj rfdetr och _create_detector gav RfDetrDetector som anropade from_checkpoint med snapshotens sökväg.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Tränade modeller registreras nu med den familj som står i manifestet i stället för hårdkodad yolo.

Ändrat:
- train_task._write_manifest skriver family i training_manifest.json.
- model_registry.trained_models läser manifestets family. Saknat eller tomt värde ger yolo, så manifest som skrevs före ändringen fungerar som förut.
- RfDetrDetector tar emot antingen en storleksnyckel eller en sökväg till en sparad viktfil. En fil laddas med rfdetr.from_checkpoint, som läser både arkitektur och antal klasser ur checkpointen. Parametern heter nu weights, som i YoloDetector.
- create_detector behövde ingen ändring eftersom den redan skickar spec.weights vidare.
- README beskriver familjens roll i modellväljaren och var RF-DETR-snapshoten hamnar.

Verifiering:
- pytest: 270 passed, 1 skipped (266 före ändringen).
- ruff check xray_detector tests: 63 fel före och efter, inga nya i berörda filer.
- Manuell GUI-kontroll med en påhittad RF-DETR-körning under models/trained/v3: posten hamnade i modellväljaren med familj rfdetr och _create_detector gav RfDetrDetector som anropade from_checkpoint med snapshotens sökväg.

Kvarstående risker:
- TASK-47 är fortfarande öppen. Till dess skriver en ny körning med samma basmodell och datasetversion över föregående manifest och vikter, och RF-DETR-manifestet pekar på senast ändrade .pth (last_ema.pth) i stället för checkpoint_best_total.pth. En RF-DETR-snapshot laddas alltså med rätt detektor, men kan vara slutvikterna och inte den bästa checkpointen.
- rfdetr.from_checkpoint krävs för att läsa en snapshot. Projektet anger rfdetr>=1.7 men låser 1.11.2 i uv.lock; en äldre 1.7-installation utan from_checkpoint skulle ge AttributeError vid laddning.
<!-- SECTION:FINAL_SUMMARY:END -->
