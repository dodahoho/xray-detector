---
id: TASK-162
title: Träning - Learning rate som parameter
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-19T09:13:00Z'
updated_date: '2026-11-19T18:02:00Z'
labels: []
dependencies: []
type: feature
ordinal: 309000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Vid små dataset <1000 samples vill man hålla learning rate låg för att undvika overfitting.

Lägg in learning rate som en justerbar parameter i träningsvyn och sätt defaultvärdet till 5e-5
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Learning rate är en justerbar parameter i träningsvyns inställningskort.
- [x] #2 Defaultvärdet är 5e-5.
- [x] #3 Värdet skickas till träningsprocessen och används som lr0 för YOLO och lr för RF-DETR.
- [x] #4 Värdet sparas i manifestets hyperparameters, så en genomförd körning går att läsa av efteråt.
- [x] #5 Värdet sparas mellan starterna och återställs i vyn.
- [x] #6 docs/beteende.md beskriver parametern och dess default.
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
1. Lägg till DEFAULT_LEARNING_RATE = 5e-5 och fältet learning_rate i TrainConfig (domain/training.py).
2. Skicka --learning-rate från TrainingWorker till träningsprocessen.
3. Ta emot parametern i train_task.py: lr0 för YOLO, lr för RF-DETR, och skriv värdet i manifestets hyperparameters.
4. Lägg in ett Learning rate-fält i träningsvyns inställningskort, spara det i training/learning_rate och skicka med i TrainConfig.
5. Uppdatera docs/beteende.md.
6. Tester för default, worker-kommando, YOLO/RF-DETR-anrop, manifest och vyns fält; kör pytest och ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering:
- AC1: TrainingView.lr_spin är en QDoubleSpinBox i träningsinställningarnas FormCard med etiketten "Inlärningshastighet:". test_training_learning_rate.py::test_the_training_view_starts_at_the_default_learning_rate instansierar vyn och läser fältet; test_form_width.py kontrollerar att fältet ryms i kortet.
- AC2: DEFAULT_LEARNING_RATE = 5e-5 i domain/training.py och TrainConfig.learning_rate har samma default. Vyn visar 0,000050 (5e-05) vid start.
- AC3: TrainingWorker.command() skickar --learning-rate med konfigurationens värde. train_task._train_yolo skickar lr0=args.learning_rate och _train_rfdetr skickar lr=args.learning_rate. Testerna test_the_worker_passes_the_learning_rate_to_the_training_process, test_yolo_training_uses_the_learning_rate_as_lr0 och test_rfdetr_training_uses_the_learning_rate_as_lr registrerar anropen.
- AC4: _hyperparameters skriver lr0 för YOLO och lr för RF-DETR. test_the_manifest_records_the_learning_rate och test_the_rfdetr_manifest_records_the_learning_rate läser manifestet.
- AC5: Värdet sparas i training/learning_rate i save_settings och läses i restore_settings; test_the_learning_rate_is_saved_and_restored gör en tur genom QSettings.
- AC6: docs/beteende.md beskriver fältet, defaulten och att värdet går till YOLO som lr0 och RF-DETR som lr.

Tester: uv run pytest -q -p no:xdist gav 980 passed, 1 skipped. uv run ruff check . går igenom.

Noteringar:
- YOLO:s lr0-default ändras från 0.001 till 5e-5, vilket är avsikten med uppgiften. scripts/variation_eval.py anropar train_task utan --learning-rate och följer därför appens nya default; rapporterna i docs/rapporter anger inget lr0-värde.
- RF-DETR:s lr_encoder lämnas på paketets 1.5e-4, eftersom uppgiften gäller en enda justerbar learning rate.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Learning rate är nu en justerbar parameter i träningsvyns inställningskort med 5e-5 som default, eftersom dataset under 1000 samples överanpassas snabbt med ramverkens egna värden. Värdet följer med TrainConfig hela vägen till träningsprocessen: YOLO får det som lr0 och RF-DETR som lr, och det skrivs i manifestets hyperparameters så en körning går att läsa av efteråt. Fältet sparas i training/learning_rate och återställs vid start. docs/beteende.md beskriver parametern. Verifierat med uv run pytest -q -p no:xdist (980 passed, 1 skipped) och uv run ruff check . (inga anmärkningar). YOLO:s lr0-default ändras därmed från 0.001 till 5e-5, vilket är avsikten; RF-DETR:s lr_encoder lämnas på paketets eget värde eftersom uppgiften gäller en enda learning rate.
<!-- SECTION:FINAL_SUMMARY:END -->
