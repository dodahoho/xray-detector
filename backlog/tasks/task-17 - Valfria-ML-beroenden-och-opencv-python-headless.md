---
id: TASK-17
title: Valfria ML-beroenden och opencv-python-headless
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - arkitektur
  - beroenden
  - pyproject
dependencies: []
references:
  - app
priority: low
type: chore
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode-bigpickle och opencode-deepseek-flash gör PyTorch/ultralytics/rfdetr till valfria extras (ml/detection) och använder opencv-python-headless, så programmet och testerna kan köras utan CUDA-paket, med detektion avstängd eller FakeDetector. Se jämförelse_glm53.md punkt 7 och jämförelse_qwen38.md.

Ändra pyproject.toml: flytta ultralytics/torch/torchvision till ett ml-extra, byt till opencv-python-headless, se till att GUI:t startar och visar video utan extras med tydlig status att detektion kräver installation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 uv sync (utan extras) ger en körbar app med ström往上 men utan detektion
- [ ] #2 uv sync --extra ml ger fullständigt detektions- och träningstöd
<!-- AC:END -->
