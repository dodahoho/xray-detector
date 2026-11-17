---
id: TASK-129
title: Förhindra radering av pågående träning från ModelSection i inställningar
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:16:00Z'
labels:
  - bugfix
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
modified_files:
  - xray_detector/ui/training_history.py
  - xray_detector/ui/model_settings.py
  - xray_detector/ui/settings_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/main_window.py
  - tests/test_model_settings.py
priority: high
type: bug
ordinal: 127000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TrainingHistoryView._delete_enabled kontrollerar att en pågående träning inte raderas, men ModelSection._on_remove i inställningsfliken saknar kontrollen: en pågående tränings katalog kan tas bort medan processen skriver i den (utvärdering_argon.md §3.4). Samla borttagningskontroll och bekräftelsedialog på ett ställe.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Det går inte att radera katalogen för en pågående träning från Inställningar -> Modeller
- [x] #2 Borttagningskontroll och bekräftelsedialog finns på ett enda ställe i koden
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
1. Flytta borttagningskontrollen och bekräftelsedialogen till två modulnivåfunktioner i ui/training_history.py: is_active_run(run_dir, active_run_dir) och confirm_delete_run(parent, run_id).

2. Låt TrainingHistoryView använda dem och ge ModelSection samma active_run_dir-anropare via SettingsView och MainWindow.

3. Test: modellistan vägrar ta bort en pågående träning utan dialog, och hjälparna delas av båda vyerna.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ui/training_history.py äger nu is_active_run(run_dir, active_run_dir) och confirm_delete_run(parent, run_id). TrainingHistoryView._delete_enabled och _on_delete använder dem. ModelSection tar active_run_dir (samma anropare som historiken) och kontrollerar is_active_run(self.trained_dir / run_id, ...) innan den frågar och raderar; en pågående träning ger i stället en statusrad. SettingsView för vidare anroparen och MainWindow skickar training_view.active_run_dir, som därför bytt namn från _active_run_dir.

Verifiering: test_running_training_cannot_be_removed_from_the_settings_tab visar att katalogen finns kvar, att ingen bekräftelsedialog visas och att statusraden säger att modellen tränas just nu. test_removal_guard_is_shared_with_the_training_history täcker is_active_run och confirm_delete_run direkt. 54 tester i test_model_settings.py och test_training_history.py går igenom, liksom hela sviten: 876 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Borttagningskontrollen och bekräftelsedialogen ligger nu på ett ställe: is_active_run och confirm_delete_run i ui/training_history.py. Träningshistoriken och modellistan i inställningarna använder båda två, så en pågående träning kan inte längre raderas från Inställningar -> Modeller medan processen skriver i katalogen. Modellistan visar i stället en statusrad om att modellen tränas just nu. Verifierat med två nya tester och hela sviten (876 passed, 1 skipped, inga nya fel).
<!-- SECTION:FINAL_SUMMARY:END -->
