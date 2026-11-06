---
id: TASK-15
title: Extern konfigfil (YAML) och loggning (loguru)
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - arkitektur
  - konfiguration
  - loggning
dependencies: []
references:
  - config
  - app
priority: low
type: task
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vscode-qwen38 har bäst konfig- och logg-hantering: Pydantic v2-config med validering plus loguru med filrotation; antigravity/bigpickle använder externa YAML-filer för klasser, kameror och trösklar. Se jämförelse_glm53.md punkt 6 och jämförelse_qwen38.md.

vibe-glm53 har i dag hårdkodad AppConfig-dataclass plus QSettings. Lägg till valfria extern konfigfil (config.yaml) för defaultklasser, kameraindex och trösklar (läses vid start om den finns), samt strukturerad loggning med rotation till logs/ i stället för statusradstexter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 klasser/kameror/trösklar kan åsidosättas från en YAML-fil
- [ ] #2 appens händelser loggas med rotation till fil
<!-- AC:END -->
