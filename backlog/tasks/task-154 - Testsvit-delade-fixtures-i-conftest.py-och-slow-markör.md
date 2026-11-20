---
id: TASK-154
title: 'Testsvit: delade fixtures i conftest.py och slow-markör'
status: Done
assignee: []
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-17T22:38:00Z'
labels:
  - testing
  - review-followup
dependencies:
  - TASK-123
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - tests/conftest.py
  - tests/test_annotation_classes.py
  - tests/test_annotation_navigation.py
  - tests/test_annotation_save_button.py
  - tests/test_annotation_ux.py
  - tests/test_app_icon.py
  - tests/test_busy_operations.py
  - tests/test_dataset_card_click.py
  - tests/test_dataset_classes.py
  - tests/test_dataset_filter.py
  - tests/test_dataset_header.py
  - tests/test_dataset_layout.py
  - tests/test_dataset_selection.py
  - tests/test_dataset_sort.py
  - tests/test_dataset_thumbnails.py
  - tests/test_dataset_variation_view.py
  - tests/test_detection_badge.py
  - tests/test_form_width.py
  - tests/test_gui_smoke.py
  - tests/test_model_settings.py
  - tests/test_pending.py
  - tests/test_settings_dialog.py
  - tests/test_shortcuts.py
  - tests/test_style.py
  - tests/test_training_imgsz.py
  - tests/test_video_file_dialog.py
  - tests/test_video_modes.py
priority: low
type: chore
ordinal: 320000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
settings-fixturen dupliceras i 16 testfiler, service i 10, window i 7, view i 6 (två settings-fixtures är identiska) (review_vibe_deepseek41_flash.md §8). Flytta settings och en tom service till conftest.py; filer som behöver förberett innehåll behåller en egen fixture med annat namn. slow-markören från TASK-123 används för MainWindow-startande tester.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 settings och tom service finns i conftest.py och dubblett-fixtures är borttagna
- [x] #2 pytest -m "not slow" kör en snabb svit; hela sviten passerar
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
1. Flytta settings-fixturen till tests/conftest.py och ta bort de 16 identiska kopiorna.

2. Sätt pytestmark = pytest.mark.slow i de testmoduler som startar MainWindow.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
settings-fixturen ligger nu i tests/conftest.py och de 16 identiska kopiorna är borttagna; filer som behöver förberett innehåll har kvar sina egna fixtures med egna namn. slow-markören från TASK-123 sätts modulvis med pytestmark i de 14 testmoduler som startar MainWindow.

Verifiering: uv run pytest -q -n auto -m 'not slow' kör 691 tester på 13 s mot 885 på 16 s för hela sviten, så den snabba sviten är meningsfull. Hela sviten: 885 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
settings-fixturen finns nu bara i tests/conftest.py; de 16 identiska kopiorna är borta. slow-markören från TASK-123 sätts modulvis i de 14 testmoduler som startar MainWindow, så uv run pytest -m 'not slow' kör 691 tester på 13 s medan hela sviten fortfarande går igenom (885 passed, 1 skipped, inga nya fel).
<!-- SECTION:FINAL_SUMMARY:END -->
