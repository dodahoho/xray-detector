---
id: TASK-3
title: Sätt atomisk skrivning av dataset.json (tempfil + os.replace)
status: To Do
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - robusthet
  - dataset
dependencies: []
references:
  - dataset
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
- [ ] #1 alla JSON-filer i datalagret skrivs via tempfil + os.replace (ingen direkt write)
- [ ] #2 en krasch under skrivning lämnar den gamla intakta filen kvar
<!-- AC:END -->
