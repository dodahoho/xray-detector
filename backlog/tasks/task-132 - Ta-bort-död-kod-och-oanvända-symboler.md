---
id: TASK-132
title: Ta bort död kod och oanvända symboler
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:20:00Z'
labels:
  - cleanup
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/domain/config.py
  - xray_detector/application/app_config.py
  - xray_detector/application/model_registry.py
  - xray_detector/application/evaluation.py
  - xray_detector/infrastructure/video/devices.py
  - xray_detector/ui/training_history.py
  - tests/test_app_config.py
  - tests/test_annotation_classes.py
  - tests/test_startup_logging.py
  - README.md
priority: medium
type: chore
ordinal: 130000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
AST-skanning och utvärderingarna hittar oanvända symboler: load_config() (domain/config.py), _parse_scalar() (application/app_config.py), spec_by_key() (application/model_registry.py), device_is_available() (infrastructure/video/devices.py), AppConfig.classes (kvarleva, data.yaml är master), SPLITS (application/evaluation.py), NO_RUNS (ui/training_history.py), oanvänd QColor-import (ui/detection_view.py), oanvänd mode-tilldelning (application/training_service.py). Ta bort dem inklusive testreferenser (utvärdering_argon.md §2.1, review_vibe_deepseek41_flash.md P3.1).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ingen av de uppräknade symbolerna finns kvar i produktionskoden
- [x] #2 ruff check rapporterar inga nya F401/F841 efter borttagningen
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
1. Ta bort load_config, _parse_scalar, spec_by_key, device_is_available, SPLITS och NO_RUNS.

2. Ta bort AppConfig.classes med dess YAML-hantering och loggning, eftersom data.yaml är master för klasslistan.

3. Uppdatera testerna som refererade symbolerna och README-raden om classes i config.yaml.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Borttaget: load_config (domain/config.py), _parse_scalar (application/app_config.py), spec_by_key (application/model_registry.py), device_is_available (infrastructure/video/devices.py, och därmed cv2-importen), SPLITS (application/evaluation.py) och NO_RUNS (ui/training_history.py). AppConfig.classes är borta tillsammans med classes-hanteringen i apply_yaml_overrides och classes i config_values; data.yaml är master för klasslistan. README-raden som påstod att classes i config.yaml är datasetets etiketter är borttagen.

Den oanvända QColor-importen i ui/detection_view.py fanns inte kvar - ruff åtgärdade den i TASK-122. Den påstått oanvända mode-tilldelningen i application/training_service.py reproducerar inte: self.mode läses av has_queued(), condition_met(), queued_status() och _check(), så den lämnas orörd.

Verifiering: ruff check . utan anmärkning (inga F401/F841). Testerna som rörde de borttagna symbolerna är omskrivna: test_yaml_overrides_model_and_threshold, test_missing_yaml_is_noop, test_config_has_no_class_list_of_its_own, och startup-loggens klasskontroll är borta. Hela sviten: 880 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Död kod är borta: load_config, _parse_scalar, spec_by_key, device_is_available, SPLITS, NO_RUNS och AppConfig.classes med sin YAML-hantering. Klasslistan har därmed en källa, data.yaml, och README påstår inte längre något annat. Två av de uppräknade fynden fanns inte kvar: QColor-importen åtgärdades i TASK-122 och mode-tilldelningen i training_service läses faktiskt av schemaläggaren. ruff utan anmärkning och hela sviten grön förutom de fyra kända Windows-offscreen-felen.
<!-- SECTION:FINAL_SUMMARY:END -->
