---
id: TASK-92
title: YOLO-träningen använder ultralytics defaults för optimizer och augmentation
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:26:00Z'
updated_date: '2026-11-16T19:17:00Z'
labels: []
dependencies: []
priority: high
type: enhancement
ordinal: 90000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-89. `train_task.py:_train_yolo` skickar bara data, epochs, imgsz, batch, device, project, name, exist_ok och patience. Allt annat blir ultralytics defaults, och flera av dem passar dåligt för röntgen. `optimizer=auto` väljer SGD eller AdamW utifrån epokantal, så samma konfiguration kan ge olika optimerare vid olika epokantal. `degrees=0.0` betyder ingen rotation alls, trots att objekten i röntgenbilderna ligger på godtycklig ledd. `mosaic=1.0` limmar ihop fyra bilder till en, vilket för röntgen skapar scener som inte finns på riktigt. `hsv_s=0.7` ändrar mättnaden kraftigt i en nästan gråskalig bild. `seed=0` är satt men inte till ett värde som dokumenterats som projektets. Referens: xray_modeltrainer använder AdamW, lr0 0.001, cos_lr, seed 42, mosaic 0.3, close_mosaic 15, degrees 30 och hsv_s 0.2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 YOLO-träningen sätter optimizer, lr0, cos_lr och seed explicit i stället för att ärva auto
- [x] #2 Augmentationen är vald för röntgen: rotation tillåts, mosaic är nedtonad och mättnadsändringen är begränsad
- [x] #3 Värdena går att läsa ut ur en genomförd körnings manifest
- [x] #4 Test täcker att de explicita värdena hamnar i anropet till model.train
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
1. Samla YOLO:ts hyperparametrar i en konstant: optimizer AdamW, lr0 0.001, cos_lr, seed 42, deterministic, mosaic 0.3, close_mosaic 15, degrees 30, translate 0.1, scale 0.5, fliplr 0.5, flipud 0, hsv_h 0.015, hsv_s 0.2, hsv_v 0.4.
2. Skicka dem explicit till model.train i _train_yolo i stället för att ärva ultralytics auto-värden.
3. Skriv samma värden som hyperparameters i manifestet så en genomförd körning går att läsa av.
4. Test med fejkad ultralytics-modul som fångar model.train-anropet.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- train_task.py: YOLO_HYPERPARAMETERS med optimizer AdamW, lr0 0.001, cos_lr, seed 42, deterministic, mosaic 0.3, close_mosaic 15, degrees 30, translate 0.1, scale 0.5, fliplr 0.5, flipud 0, hsv_h 0.015, hsv_s 0.2, hsv_v 0.4. Skickas explicit till model.train i _train_yolo.
- Manifestet får hyperparameters via _hyperparameters(args): YOLO:s värden som de skickas, RF-DETR:s resolution/num_workers/seed.

Verifiering: tests/test_training_params.py täcker att värdena hamnar i model.train-anropet (fejkad ultralytics-modul) och att de går att läsa ur manifestet. Hela sviten: 747 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
YOLO-träningen ärver inte längre ultralytics defaults. Optimizer, inlärningshastighet, cosinus-schema och seed sätts explicit (AdamW, lr0 0.001, cos_lr, seed 42, deterministic), eftersom optimizer=auto väljer SGD eller AdamW utifrån epokantalet och samma konfiguration därför kunde ge olika optimerare. Augmentationen är vald för röntgen: rotation tillåts (degrees 30) eftersom objekten ligger på godtycklig ledd, mosaic är nedtonad till 0.3 med close_mosaic 15 så scener som inte finns på riktigt inte dominerar, och mättnadsändringen är begränsad till hsv_s 0.2 i stället för 0.7 i en nästan gråskalig bild. Samma värden skrivs i manifestets hyperparameters, så en genomförd körning går att läsa av efteråt.

Verifiering: tests/test_training_params.py täcker med en fejkad ultralytics-modul att värdena hamnar i model.train-anropet och att de går att läsa ur manifestet. Hela sviten: 747 passed, 1 skipped.

Risk: värdena är hämtade från xray_modeltrainer och inte omtränade mot det här datasetet; de är en rimlig utgångspunkt, inte en optimerad konfiguration.
<!-- SECTION:FINAL_SUMMARY:END -->
