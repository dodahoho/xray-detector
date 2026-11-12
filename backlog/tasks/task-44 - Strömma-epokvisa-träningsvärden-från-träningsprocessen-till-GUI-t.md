---
id: TASK-44
title: Träning - Strömma epokvisa träningsvärden från träningsprocessen till GUI:t
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T11:51:00Z'
updated_date: '2026-11-12T09:39:00Z'
labels: []
dependencies: []
references:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/ui/training_view.py
modified_files:
  - README.md
  - xray_detector/domain/training.py
  - xray_detector/infrastructure/training/epoch_metrics.py
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/ui/training_view.py
  - tests/test_epoch_metrics.py
  - tests/test_log_layout.py
  - tests/test_model_layout.py
priority: high
type: feature
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Träningsvyn visar i dag bara träningsprocessens råa stdout i en QPlainTextEdit. Det finns ingen progressbar, ingen epokräknare och inga strukturerade värden. TrainingWorker har bara signalen progress(str), så GUI:t kan inte veta vilken epok som körs eller hur loss och mAP utvecklas utan att parsa fri text.

Verifierat i befintlig kod och med en riktig 1-epokskörning:
- TrainingWorker._on_stdout läser all tillgänglig data och delar på radbrytning. Skrivs en rad i två delar, vilket ultralytics tqdm gör hela tiden, blir första halvan en egen loggrad och resten en annan. Empiriskt hamnade "epoch 1/10 " och "loss=1.23" som två separata rader.
- train_task._read_metrics läser bara sista raden i results.csv och bara kolumner som börjar med metrics/. Train- och val-losserna (train/box_loss, val/box_loss osv.) filtreras bort. Den anropas dessutom först efter avslutad träning, för manifestet.
- RF-DETR skriver metrics.csv via PyTorch Lightning CSVLogger i output_dir, inte results.csv, så _read_metrics ger tomma metrics för RF-DETR.
- Ultralytics results.csv innehåller per epok: train/box_loss, train/cls_loss, train/l1_loss, metrics/precision(B), metrics/recall(B), metrics/mAP50(B), metrics/mAP50-95(B), val/box_loss, val/cls_loss, val/l1_loss och lr/pg*.
- RF-DETR metrics.csv innehåller train/loss, val/loss, val/mAP_50_95, val/mAP_50, val/mAP_75, val/mAR, val/F1, val/precision och val/recall.

Kravet är att träningsprocessen rapporterar ett strukturerat event per epok för både YOLO och RF-DETR, att GUI:t visar progressbar med epok X/Y och aktuella värden, och att loggen behålls. Partiella rader ska buffras tills radbrytning.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Träningsprocessen skickar ett strukturerat epokevent för YOLO
- [ ] #2 Träningsprocessen skickar ett strukturerat epokevent för RF-DETR
- [ ] #3 Eventet innehåller epok, totalt antal epoker, train-loss, val-loss, mAP50, mAP50-95, precision och recall
- [ ] #4 TrainingWorker exponerar en strukturerad signal som GUI:t kan koppla till, inte bara strängar
- [ ] #5 Träningsvyn visar en progressbar med epok X/Y och de aktuella värdena
- [ ] #6 Loggen visar fortfarande processens råa utmatning
- [ ] #7 Partiella rader från processen buffras och loggas som en rad
- [ ] #8 Tester täcker parsning för både YOLO- och RF-DETR-format
<!-- AC:END -->

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
1. EpochMetrics i domain/training.py: epok, totalt antal epoker, train-loss, val-loss, mAP50, mAP50-95, precision, recall.
2. infrastructure/training/epoch_metrics.py: MetricsTail läser tillkommande rader ur results.csv (YOLO) och metrics.csv (RF-DETR), EpochAccumulator slår ihop RF-DETR:s train- och valrader per epok, EpochReporter pollar i en tråd och skriver EPOCH {json} på stdout.
3. train_task.py startar rapportören före träningen och stänger den i finally.
4. TrainingWorker buffrar partiella rader, parsar EPOCH-rader till signalen epoch_metrics och loggar en läsbar sammanfattning; övriga rader loggas råa.
5. Träningsvyn visar progressbar med epok X/Y och de aktuella värdena.
6. Tester för YOLO- och RF-DETR-parsning, buffring och signalen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Epokeventen går från träningsprocessen till GUI:t som EPOCH {json}-rader på stdout. Rapportören i träningsprocessen läser results.csv (YOLO) respektive metrics.csv (RF-DETR) och slår ihop RF-DETR:s train- och valrader per epok. TrainingWorker buffrar partiella rader och exponerar signalen epoch_metrics; träningsvyn visar progressbar med epok X/Y och värdena. Verifierat med en riktig 2-epokskörning på CPU: två EPOCH-rader med epok 1/2 och 2/2, och manifestet uppdaterat per epok.
<!-- SECTION:NOTES:END -->
