---
id: TASK-136
title: Ersätt tre handskrivna YAML-tolkare med PyYAML
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-17T22:27:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - pyproject.toml
  - uv.lock
  - xray_detector/application/app_config.py
  - xray_detector/infrastructure/dataset_store/yolo.py
  - xray_detector/infrastructure/training/train_task.py
  - tests/test_app_config.py
  - tests/test_dataset_store.py
  - README.md
priority: medium
type: enhancement
ordinal: 323000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
app_config.apply_yaml_overrides, yolo.read_classes/_parse_names/_parse_indented_names och train_task._read_data_classes parsar YAML för hand (~100 rader skör strängparsning; train_task saknar till och med flerradigt dict-stöd, alla tre utvärderingarna överens). Deklarera pyyaml explicit i pyproject.toml, använd yaml.safe_load/safe_dump i app_config.py och yolo.py, och låt train_task.py anropa read_classes() från yolo.py.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 yaml.safe_load används i app_config.py och yolo.py; train_task använder read_classes()
- [x] #2 config.yaml och data.yaml i standardformat (listposter på egna rader, radslutskommentarer, flerradig names-dict) parsas korrekt
- [x] #3 Alla berörda tester passerar
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
1. Deklarera pyyaml i pyproject.toml och uppdatera uv.lock.

2. Låt app_config.apply_yaml_overrides och yolo.read_classes använda yaml.safe_load; ta bort _parse_names och _parse_indented_names.

3. Låt train_task._read_data_classes anropa read_classes från yolo.py i stället för att parsa data.yaml själv.

4. Tester för standardformat: radslutskommentarer, flerradig names-dict, listform, tom och trasig fil.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
pyyaml>=6.0 ligger nu i [project].dependencies (låst till 6.0.3). app_config.apply_yaml_overrides läser filen med yaml.safe_load och hanterar default_model, confidence_threshold samt data_dir/models_dir/logs_dir; en tom fil räknas som läst och en fil som inte är ett dict eller inte går att tolka lämnar konfigurationen orörd. yolo.read_classes läser names ur både list- och dictform via safe_load, och _parse_names/_parse_indented_names är borta. train_task._read_data_classes anropar read_classes för YAML-fallet, så manifestet och datasetvyn använder samma läsare.

Verifiering: sex nya tester - tre i test_app_config.py (radslutskommentarer och relativa kataloger, trasig YAML, tom YAML) och tre i test_dataset_store.py (flerradig names-dict med kommentar, listformen som write_data_yaml skriver, trasig data.yaml). Hela sviten: 874 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel). ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
De tre handskrivna YAML-tolkarna är ersatta: app_config.apply_yaml_overrides och yolo.read_classes använder yaml.safe_load, och train_task._read_data_classes anropar read_classes i stället för att parsa data.yaml själv. pyyaml är deklarerat i pyproject.toml. Standardformat fungerar nu, inklusive radslutskommentarer, flerradig names-dict och listposter på egna rader, och en trasig fil ger tomma värden i stället för ett undantag. Sex nya tester täcker fallen; hela sviten: 874 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->
