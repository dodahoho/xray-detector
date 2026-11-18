---
id: TASK-91
title: RF-DETR-träning får inte bildstorlek, workers eller seed
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:26:00Z'
updated_date: '2026-11-16T19:17:00Z'
labels: []
dependencies: []
priority: high
type: bug
ordinal: 206000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-89. `train_task.py:_train_rfdetr` skickar bara `dataset_dir`, `epochs`, `batch_size`, `device` och early stopping. Tre saker faller därför bort tyst. `resolution` ligger i `rfdetr.config.ModelConfig`, inte i `TrainConfig`, så den måste sättas när modellen konstrueras — i dag når GUI:ts bildstorlek aldrig RF-DETR, och användaren får en annan upplösning än den som står i vyn. `num_workers` har default 2, vilket svälter GPU:n på ett stort dataset. `seed` har default None, så körningen är inte reproducerbar. Dessutom är batch default 16 för båda familjerna, men RF-DETR large får OOM på ett 16 GB-kort vid resolution 704 och kan inte återhämta sig eftersom CUDA-kontexten redan är förstörd när paketet anropar empty_cache().
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Bildstorleken i träningsvyn styr RF-DETR-modellens resolution
- [x] #2 En resolution som inte är delbar med patch_size * num_windows avvisas med ett tydligt fel innan träningen startar
- [x] #3 RF-DETR-träningen sätter num_workers och seed explicit
- [x] #4 Batch-default skiljer sig mellan YOLO och RF-DETR så att RF-DETR large inte får OOM på ett 16 GB-kort
- [x] #5 Test täcker att resolution och num_workers hamnar i anropet till rfdetr
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
1. Lägg RFDETR_RESOLUTION_DIVISOR (32 = patch_size 16 x num_windows 2) och rfdetr_resolution_error() i domain/training.py.
2. Sätt resolution när RF-DETR-modellen konstrueras i _train_rfdetr och skicka num_workers och seed explicit.
3. Avvisa en resolution som inte är delbar med 32 i main() innan körningskatalogen skapas, och i träningsvyn innan processen startas.
4. Familjeberoende batch-default: 16 för YOLO, 4 för RF-DETR; träningsvyn följer familjen tills användaren väljer ett eget värde.
5. Test med fejkad rfdetr-modul som fångar konstruktorns och train-anropets argument.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- domain/training.py: RFDETR_RESOLUTION_DIVISOR (32), rfdetr_resolution_error(), DEFAULT_BATCH per familj, default_batch() och TrainConfig.batch_size().
- train_task.py: _train_rfdetr konstruerar modellen med resolution=args.imgsz och skickar num_workers (default 8) och seed (default 42) explicit. Nya CLI-argument --workers och --seed; --batch defaultar per familj.
- main() avvisar en RF-DETR-upplösning som inte är delbar med 32 innan körningskatalogen skapas (exit 2), och träningsvyn avvisar samma storlek i statusraden innan processen startas.
- Träningsvyns batch-fält följer familjen (16 YOLO, 4 RF-DETR) tills användaren väljer ett eget värde; först då sparas training/batch.

Verifiering: tests/test_training_params.py (14 tester) plus uppdaterade test_rfdetr.py. Hela sviten: 747 passed, 1 skipped. CLI:t manuellt kontrollerat: --imgsz 650 med --family rfdetr ger 'Fel: RF-DETR kräver en bildstorlek som är delbar med 32 ...' och exit 2 utan att skapa katalogen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RF-DETR-träningen fick de tre parametrar som tidigare föll bort tyst. Bildstorleken i träningsvyn sätts nu som modellens resolution när modellen konstrueras, och en storlek som inte är delbar med 32 (patch_size 16 x num_windows 2) avvisas med ett tydligt fel innan träningen startar — både i vyn och i träningsprocessen, som avvisar den innan körningskatalogen skapas. num_workers (8) och seed (42) skickas explicit i stället för paketets 2 respektive None. Batch-defaulten skiljer sig mellan familjerna: 16 för YOLO och 4 för RF-DETR, eftersom RF-DETR large får OOM på ett 16 GB-kort vid resolution 704 med batch 16 och CUDA-kontexten inte går att rädda efter det. Träningsvyns batch-fält följer familjen tills användaren väljer ett eget värde.

Verifiering: tests/test_training_params.py (14 tester) och uppdaterade test_rfdetr.py; hela sviten 747 passed, 1 skipped. CLI:t manuellt kontrollerat: --imgsz 650 med --family rfdetr ger exit 2 och ett fel som namnger delbarheten, utan att skapa körningskatalogen.

Risk: rfdetr:s train()-signatur varierar mellan versioner, så kwargs filtreras fortfarande mot den faktiska signaturen. Resolutionen sätts i konstruktorn, vilket rfdetr 1.11 stöder.
<!-- SECTION:FINAL_SUMMARY:END -->
