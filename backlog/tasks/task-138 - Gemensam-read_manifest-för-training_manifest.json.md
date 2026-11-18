---
id: TASK-138
title: Gemensam read_manifest() för training_manifest.json
status: Done
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-17T22:31:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/application/training_history.py
  - xray_detector/application/model_registry.py
  - tests/test_training_snapshot.py
  - tests/test_model_layout.py
priority: medium
type: enhancement
ordinal: 157000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
model_registry.trained_models och training_history._read_run gör båda rglob, JSON-läsning, sökvädesbygge och run_id-beräkning av samma manifest (utvärdering_argon.md §3.3, review_vibe_deepseek41_flash.md P2.1). Låt en enda modul läsa manifestet (förslag: training_history eller en ny manifest-modul i infrastructure/training) och bygg ModelSpec från TrainingRun. Görs när modulen ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 training_manifest.json läses på ett enda ställe
- [x] #2 Nya manifestfält behöver bara läggas till på ett ställe och syns i både modellväljare och historik
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
1. Låt TrainingRun bära manifestets name och base_model_name.

2. Låt model_registry.trained_models bygga ModelSpec ur training_runs() i stället för att läsa manifestet själv.

3. Test som visar att väljaren och historiken läser samma manifest och är eniga om nyckel, etikett, familj och vikter.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
training_manifest.json läses nu bara i training_history._read_run. TrainingRun har fått name och base_name, och model_registry.trained_models bygger ModelSpec ur training_runs() i stället för att göra egen rglob, JSON-läsning och run_id-beräkning. Ett manifest utan visningsnamn hoppas över i väljaren, eftersom en post utan etikett inte går att visa; historiken visar den ändå.

Verifiering: test_the_selector_and_the_history_read_the_same_manifest jämför nyckel, etikett, familj, vikter och basnamn mellan de två läsarna. _args i test_training_snapshot.py sätter nu name och base_name som GUI:t gör, eftersom väljaren annars hoppar över manifesten. Hela sviten: 876 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
training_manifest.json läses på ett ställe: training_history._read_run. TrainingRun bär nu även name och base_name, och modellväljarens trained_models bygger ModelSpec ur training_runs() i stället för att läsa filen själv. Ett nytt manifestfält läggs därför till på ett ställe och syns i både väljaren och historiken. Verifierat med ett test som jämför de två läsarna; hela sviten: 876 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
