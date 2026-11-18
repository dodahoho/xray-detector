---
id: TASK-143
title: Dokumentera lagerfasaden och bryt cykliskt beroende rfdetr_detector
status: Done
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-18T07:50:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
priority: medium
type: enhancement
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ui importerar infrastructure på fem ställen, application importerar infrastructure i fem av åtta moduler, och rfdetr_detector.py importerar application.app_config (cykliskt) (alla tre utvärderingarna). Vid motsägelsen mellan strukturell ombyggnad och dokumentation väljs enklaste först: dokumentera i README/groma att application är en fasad bredvid infrastructure och vilka importregler som gäller; flytta augment-konstanter (MIN_SCALE/MAX_SCALE/describe) till domain/dataset.py; bryt det cykliska beroendet genom att flytta loggfångsten till infrastructure/logging.py eller en callback.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README/groma beskriver tydligt att application är en fasad och vilka importregler som gäller
- [x] #2 Inget cykliskt beroende infrastructure -> application finns kvar
- [x] #3 MIN_SCALE/MAX_SCALE/describe ligger i domain/dataset.py och ui importerar dem därifrån
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
1. Flytta loggfångsten (CAPTURED_LOGGERS, NOISY_LOGGERS, _matches, capture_third_party_logs) till infrastructure/logging.py och låt application/app_config.py importera den därifrån, så infrastructure inte längre importerar application.
2. Flytta MIN_SCALE, MAX_SCALE och describe till domain/dataset.py; augment.py importerar dem och ui importerar dem från domain.
3. Dokumentera lagerreglerna i README: application är en fasad över infrastructure, och infrastructure importerar aldrig application.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Genomfört: infrastructure/logging.py äger loggfångsten; app_config importerar capture_third_party_logs därifrån och rfdetr_detector importerar den direkt, så det lokala application-importet i infrastructure är borta. grep efter xray_detector.application i xray_detector/infrastructure/ är tomt. MIN_SCALE/MAX_SCALE/describe ligger i domain/dataset.py; dataset_view och variation_dialog importerar dem därifrån och augment.py importerar dem för klämningen. README har en ny Kodstruktur-sektion med lagerreglerna. ui importerar fortfarande infrastructure på tre ställen i detection_view (BaseDetector, ResourceMonitor, list_device_modes); det är dokumenterat som tillåtet för rena typer och enhetslistor som saknar fasad.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Loggfångsten flyttade från application/app_config.py till infrastructure/logging.py, så infrastructure inte längre importerar application; rfdetr_detector importerar capture_third_party_logs därifrån och grep efter xray_detector.application i xray_detector/infrastructure/ är tomt. MIN_SCALE, MAX_SCALE och describe ligger i domain/dataset.py; dataset_view och variation_dialog importerar dem därifrån och augment.py importerar dem för klämningen. README har en ny Kodstruktur-sektion som beskriver att application är en fasad över infrastructure, att infrastructure aldrig importerar application, och att ui bara importerar infrastructure för rena typer och enhetslistor som saknar fasad. Verifierat med uv run ruff check . och uv run pytest -q (889 passed, 1 skipped).
<!-- SECTION:FINAL_SUMMARY:END -->
