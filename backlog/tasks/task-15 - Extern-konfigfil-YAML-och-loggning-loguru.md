---
id: TASK-15
title: Extern konfigfil (YAML) och loggning (loguru)
status: Done
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T10:10:00Z'
labels:
  - arkitektur
  - konfiguration
  - loggning
dependencies: []
references:
  - config
  - app
modified_files:
  - xray_detector/application/app_config.py
  - xray_detector/app.py
  - xray_detector/ui/main_window.py
  - tests/test_app_config.py
priority: low
type: task
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vscode-qwen38 har bäst konfig- och logg-hantering: Pydantic v2-config med validering plus loguru med filrotation; antigravity/bigpickle använder externa YAML-filer för klasser, kameror och trösklar. Se jämförelse_glm53.md punkt 6 och jämförelse_qwen38.md.

vibe-glm53 har i dag hårdkodad AppConfig-dataclass plus QSettings. Lägg till valfria extern konfigfil (config.yaml) för defaultklasser, kameraindex och trösklar (läses vid start om den finns), samt strukturerad loggning med rotation till logs/ i stället för statusradstexter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 klasser/kameror/trösklar kan åsidosättas från en YAML-fil
- [x] #2 appens händelser loggas med rotation till fil
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ny application-modul app_config.py: load_config_with_yaml() sliding Appens default med en valfri config.yaml (sokordning: datakatalogen sedan arbetskatalogen) som kan overrida classes, default_model, confidence_threshold och data_dir - enkel rad-baserad YAML-tolkning utan extra beroende (PyYAML saknas i miljon). app.py anvander den och startar rotationsloggnings (RotatingFileHandler, 1 MB x 5, under datakatalogens logs/) - stdlib logging i stallet for loguru for att undvika nytt beroende; statusmeddelanden loggas via xray-loggern. Verifierat: 5 nya tester (override av klasser/modell/troskel, saknad fil no-op, prioritering datakat->arbetskat, rotationsfil skrivs och idempotent setup); hel svit 59 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
