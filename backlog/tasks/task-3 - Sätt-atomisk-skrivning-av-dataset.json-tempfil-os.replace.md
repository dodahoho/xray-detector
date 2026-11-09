---
id: TASK-3
title: Sätt atomisk skrivning av dataset.json (tempfil + os.replace)
status: Done
assignee:
  - '@glm53'
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T12:48:00Z'
labels:
  - robusthet
  - dataset
dependencies: []
references:
  - dataset
modified_files:
  - xray_detector/infrastructure/dataset_store/json_io.py
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/infrastructure/dataset_store/export.py
  - xray_detector/infrastructure/training/train_task.py
  - tests/test_atomic_json.py
priority: high
type: enhancement
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DatasetStore skriver idag dataset.json direkt med open(w) - en krasch eller strömavbrott mitt i skrivningen kan korrumpera hela versionens index.

opencode-deepseek-flash (atomic_write_json: mkstemp + fsync + os.replace) och opencode-bigpickle löser detta med temporär fil i samma katalog och atomiskt byte. Se jämförelse_glm53.md punkt 8 och jämförelse_argon.md avsnitt 6.

Implementera en shared helper i xray_detector/dataset/store.py (eller util) och använd den för alla JSON-skrivningar (dataset.json, manifest, exportindex).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 alla JSON-filer i datalagret skrivs via tempfil + os.replace (ingen direkt write)
- [x] #2 en krasch under skrivning lämnar den gamla intakta filen kvar
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ny helper atomic_write_json i infrastructure/dataset_store/json_io.py: tempfile i samma katalog (mkstemp) + flush/fsync + os.replace, med cleanup av tempfilen vid fel. Anvands nu av alla JSON-skrivningar i datalagret: DatasetStore._save_coco (dataset.json), exportmanifest, dataset.json i COCO-exporten, RF-DETR:s per-split _annotations.coco.json samt train_tasks training_manifest.json. Verifierat: nya tester visar att en simulerad krasch mitt i skrivningen later den gamla filen intakt och att inga tempfiler latnar sig, samt att hela dataset/export-flodet fungerar oforandrat.
<!-- SECTION:FINAL_SUMMARY:END -->
