---
id: TASK-142
title: Ta bort tunna DatasetService/VideoService-fasader
status: Done
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-18T08:02:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - review_vibe_deepseek41_flash.md
priority: medium
type: enhancement
ordinal: 161000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DatasetService är 150 rader där 25 av 26 metoder är enradsdelegeringar till DatasetStore; VideoService delegerar 1-till-1 till CameraService (utvärdering_argon.md §4.1, review_vibe_deepseek41_flash.md P2.9). Vid motsägelsen väljs enklaste alternativet med minst kod: ta bort fasaderna och låt vyerna använda DatasetStore/CameraService direkt (alternativet att fasaden äger verklig logik som num_objects/exportlayout får bara väljas om det finns ett konkret behov).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Beslut är genomfört: fasaderna är borttagna eller äger verklig logik
- [x] #2 ui importerar inte längre tunna pass-through-fasader utan eget syfte
- [x] #3 Alla tester passerar
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
1. Flytta train_val_counts till export.py och lägg build_source i video/source.py.
2. Ta bort application/dataset_service.py och application/video_service.py.
3. Låt MainWindow äga en DatasetStore och låt dataset-, annoterings- och träningsvyn ta den; export- och pending-anrop går till modulfunktionerna.
4. Låt DetectionView använda CameraService och build_source direkt.
5. Uppdatera testerna och README:s Kodstruktur.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Genomfört: fasaderna är borttagna. DatasetStore används direkt av vyerna; group_count(store.load_dataset()['images']) ersätter image_pair_count, train_val_counts ligger i export.py, och export_*/pending_* anropas som modulfunktioner med store respektive config.data_dir. DetectionView använder CameraService och build_source. MainWindow.dataset_store ersätter dataset_service. README:s Kodstruktur beskriver nu application som samordning i stället för en tjänsteklass per infrastrukturmodul. Groma-kartan refererar fortfarande dataset-service.md och video-service.md; den behöver cureras separat eftersom Groma äger sina filer.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
DatasetService och VideoService är borttagna. Vyerna använder DatasetStore direkt, train_val_counts ligger i export.py, export- och pending-anropen går till modulfunktionerna, och DetectionView använder CameraService med build_source i infrastructure/video/source.py. MainWindow äger dataset_store. README:s Kodstruktur beskriver att application bara är samordning. Verifierat med uv run ruff check . och uv run pytest -q (889 passed, 1 skipped). Kvar utanför uppgiften: Groma-kartan har kvar dataset-service.md och video-service.md och behöver cureras via groma-CLI:t.
<!-- SECTION:FINAL_SUMMARY:END -->
