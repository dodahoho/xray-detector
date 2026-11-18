---
id: TASK-139
title: En enda källa för CUDA-enhetsstatus och färger i ui/colors.py
status: Done
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-17T22:33:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/infrastructure/detectors/base.py
  - xray_detector/application/model_registry.py
  - xray_detector/ui/colors.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/badge.py
  - xray_detector/ui/model_settings.py
  - xray_detector/ui/settings_dialog.py
  - xray_detector/ui/training_history.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/variation_dialog.py
  - tests/test_busy_operations.py
  - tests/test_colors.py
priority: medium
type: enhancement
ordinal: 137000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
device_status() (model_registry) och cuda_device_label() (detectors/base) gör samma torch.cuda-uppslag med olika strängar och felhantering, och färgerna #2a8/#c33 är hårdkodade i en applikationsmodul (utvärdering_argon.md §3.5, review_vibe_deepseek41_flash.md P2.4). Gör cuda_device_label() till enda källan; device_status() bygger på den och färgen flyttas till ui/colors.py. Görs när modulen ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Endast en funktion avgör enhetsstatus och båda konsumenterna använder den
- [x] #2 Inga CSS-färger hårdkodas utanför ui/colors.py
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
1. Gör cuda_device_label() i detectors/base.py till enda källan för enhetsstatus, inklusive fallet att torch saknas.

2. Låt model_registry.device_status() returnera enbart texten 'Enhet: <label>' och flytta färgvalet till ui/colors.device_color().

3. Flytta alla hårdkodade CSS-färger i ui/ och application/ till namngivna konstanter i ui/colors.py.

4. Tester: device_color, att device_status delegerar, och att inga hex-färger finns utanför colors.py.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
cuda_device_label() är enda stället som avgör om CUDA används och hanterar nu även att torch saknas ('PyTorch saknas'). model_registry.device_status() returnerar bara texten 'Enhet: <label>', så applikationslagret inte längre känner till CSS; färgen väljs av ui/colors.device_color(label).

Paletten ligger nu i ui/colors.py: TEXT_DARK, TEXT_LIGHT, MUTED_TEXT, SUBTLE_TEXT, BORDER, IDLE_BORDER, CARD_BORDER, GEAR_COLOR, SELECTED_BORDER, SELECTED_BACKGROUND, IDLE_BACKGROUND, HEADER_BACKGROUND, PENDING_COLOR, ERROR_COLOR, PANEL_BACKGROUND samt DEVICE_CUDA_COLOR/DEVICE_CPU_COLOR. Alla 30 hårdkodade literaler i ui/-modulerna är ersatta, och dataset_view:s lokala SELECTED_BORDER med flera är borta till förmån för importerna.

Verifiering: tre nya tester i test_colors.py, däribland ett som skannar xray_detector/ och fallerar om en hex-färg finns utanför colors.py. test_busy_operations.py:s fake-device_status returnerar nu bara texten. Hela sviten: 879 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Enhetsstatusen har en källa: cuda_device_label() i detectors/base.py, som även hanterar att torch saknas. device_status() bygger på den och returnerar bara texten, medan färgen väljs av ui/colors.device_color(). Hela färgpaletten ligger nu i ui/colors.py, och ett test skannar källkoden och fallerar om en hex-färg dyker upp någon annanstans. Hela sviten: 879 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
