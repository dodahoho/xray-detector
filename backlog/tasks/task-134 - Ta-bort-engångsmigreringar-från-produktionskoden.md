---
id: TASK-134
title: Ta bort engångsmigreringar från produktionskoden
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:22:00Z'
labels:
  - cleanup
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/app.py
  - xray_detector/application/model_registry.py
  - xray_detector/application/training_history.py
  - xray_detector/ui/training_view.py
  - tests/test_dataset_store.py
  - tests/test_model_layout.py
  - README.md
priority: medium
type: chore
ordinal: 132000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Alla tre utvärderingarna pekar på att _migrate_versions() och _migrate_coco() körs i DatasetStore.__init__ vid varje uppstart och _warn_about_legacy_models() i app.py. Vid motsägelsen mellan utvärderingarna väljs det enklaste alternativet med minst kod: ta bort migreringskoden i stället för att införa schema_version. Ta även bort bakåtkompatibilitet för manifest före TASK-48/TASK-108 och gamla viktfilsnamn, inklusive tillhörande migreringstester.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ingen migreringskod körs vid DatasetStore.__init__ eller appstart
- [x] #2 Migreringstester är borttagna och övriga tester passerar
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
1. Ta bort _migrate_versions och _migrate_coco ur DatasetStore.__init__ och _warn_about_legacy_models ur app.py.

2. Ta bort bakåtkompatibiliteten i manifestläsningen: name och family krävs av trained_models, family krävs av _read_run, och restore_settings letar inte längre efter gamla viktfilsnamn.

3. Ta bort migreringstesterna och README-raden om att datasets/v1 flyttas automatiskt.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Borttaget: _migrate_versions och _migrate_coco (kördes i DatasetStore.__init__), _warn_about_legacy_models (kördes vid appstart), fallback-etiketten för manifest utan name (före TASK-108), familjedefaulten yolo för manifest utan family (före TASK-48) i både trained_models och _read_run, och sökningen efter gamla viktfilsnamn i TrainingView.restore_settings. Ett manifest som saknar name, family eller weights_relative hoppas nu över i stället för att gissas, via KeyError i samma except som OSError och ValueError.

Verifiering: sex migreringstester borttagna (två i test_dataset_store.py, fyra i test_model_layout.py) och _write_run i test_model_layout skriver name som träningen gör. Sviten går från 874 till 868 passed, alltså exakt de sex borttagna testerna, och ruff är utan anmärkning. Kvar är samma fyra Windows-specifika offscreen-fel.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Engångsmigreringarna är borta: DatasetStore.__init__ rör inte längre katalogen och appstarten varnar inte om den gamla modellkatalogen. Bakåtkompatibiliteten för manifest före TASK-48/TASK-108 och för gamla viktfilsnamn är också borta; ett ofullständigt manifest hoppas över i stället för att gissas. Sex migreringstester och README-raden om automatisk flytt av datasets/v1 är borttagna, sviten går från 874 till 868 passed och ruff är utan anmärkning.
<!-- SECTION:FINAL_SUMMARY:END -->
