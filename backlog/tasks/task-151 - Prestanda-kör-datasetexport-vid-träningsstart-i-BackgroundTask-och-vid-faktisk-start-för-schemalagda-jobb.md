---
id: TASK-151
title: >-
  Prestanda: kör datasetexport vid träningsstart i BackgroundTask och vid
  faktisk start för schemalagda jobb
status: Done
assignee: []
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-18T08:22:00Z'
labels:
  - performance
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
priority: low
type: enhancement
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Export vid träningsstart körs synkront i GUI-tråden (raderar exports/ och kopierar alla bilder); schemalagda jobb exporterar vid klickögonblicket så dagens annoteringar missas; för YOLO behövs ingen bildkopiering alls om data.yaml pekar på train.txt/val.txt (utvärdering_argon.md §5.3). Flytta exporten till BackgroundTask och kör den när det schemalagda jobbet faktiskt startar.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GUI-tråden fryser inte vid träningsstart (export körs i bakgrunden)
- [x] #2 Schemalagd träning exporterar datasetet när jobbet startar, inte vid schemaläggning
- [x] #3 YOLO-träning använder train.txt/val.txt utan att kopiera bilder
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
1. Låt export_yolo skriva train.txt/val.txt med sökvägar till datasetets egna bilder och låta data.yaml peka på listorna, så inga bilder kopieras.
2. Lägg export_dataset(store, export_dir, family, ratio) som väljer export efter familj.
3. Gör TrainConfig.dataset_yaml valfri och sätt den när exporten är klar.
4. Kör exporten i en BackgroundTask i TrainingView._on_start för direkt start.
5. Låt TrainingScheduler spara exporten i kön och köra den när villkoret är uppfyllt, strax före create_worker.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Genomfört: export_yolo skriver train.txt/val.txt (absoluta sökvägar till datasetets images/) och data.yaml pekar på dem; inga bilder kopieras. export_dataset väljer YOLO eller RF-DETR. TrainConfig.dataset_yaml är Path | None och sätts av exporten; TrainingWorker.command kastar ValueError om den saknas. TrainingView._on_start skickar en export-closure: direkt start kör den i BackgroundTask och skapar workern först när data.yaml finns, schemalagda jobb sparar closuren i kön. TrainingScheduler._check kör exporten i BackgroundTask när villkoret är uppfyllt och startar sedan workern. Nya tester: test_scheduled_job_exports_when_it_starts, test_training_start_does_not_block_on_the_export, samt omskrivna export-tester för listorna.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetexporten körs inte längre i GUI-tråden: TrainingView._on_start startar en BackgroundTask och skapar workern först när data.yaml finns, och ett schemalagt jobb sparar exporten i kön och kör den när villkoret är uppfyllt, så det tränar på aktuella annoteringar. YOLO-exporten skriver train.txt och val.txt med sökvägar till datasetets egna bilder i stället för att kopiera dem, och data.yaml pekar på listorna. TrainConfig.dataset_yaml sätts av exporten och TrainingWorker vägrar bygga kommandoraden utan den. Verifierat med uv run ruff check . och uv run pytest -q (895 passed, 1 skipped) samt nya tester för schemalagd export och icke-blockerande start.
<!-- SECTION:FINAL_SUMMARY:END -->
