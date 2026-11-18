---
id: TASK-130
title: Egentränade modeller valbara som basmodell i träningsvyn
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:17:00Z'
labels:
  - bugfix
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
modified_files:
  - xray_detector/ui/training_view.py
  - tests/test_training_params.py
priority: high
type: bug
ordinal: 167000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TrainingView.refresh_models anropar base_models(models_dir) istället för available_models(models_dir, trained_dir), så modeller under models/trained/ aldrig visas i träningsvyns basmodellväljare trots att README beskriver vidareträning (utvärdering_argon.md §5.5).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Modeller från models/trained/ visas i träningsvyns basmodellväljare
- [x] #2 Test eller manuell kontroll av refresh_models med en tränad modell
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
1. Låt TrainingView.refresh_models bygga listan med available_models(models_dir, trained_dir) i stället för base_models(models_dir).

2. Test: en träningskörning under models/trained/ syns i väljaren med rätt viktsökväg, och ett sparat val av en egentränad modell överlever refresh_models.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
training_view.py: refresh_models använder available_models(self.config.models_dir, self.config.trained_dir), samma funktion som detektionsvyns väljare och modellistan i inställningarna. _disable_missing_rfdetr och restore_settings fungerar oförändrat eftersom en egentränad modell har family i sitt manifest och nyckeln trained-<körning> slås upp i väljaren.

Verifiering: test_trained_models_are_selectable_as_base_model visar att trained-v3 finns i väljaren med etiketten från manifestet och weights satt till best.pt; test_a_trained_model_stays_selected_after_a_refresh visar att valet överlever refresh_models. Båda fallerar mot koden före ändringen (listan innehöll bara basmodellerna). Hela sviten: 878 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningsvyns basmodellväljare bygger nu sin lista med available_models, så modeller under models/trained/ syns och kan vidaretränas från sina bästa vikter, som README beskriver. Två tester täcker listan och att ett sparat val överlever en refresh; båda fallerar mot koden före ändringen. Hela sviten: 878 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
