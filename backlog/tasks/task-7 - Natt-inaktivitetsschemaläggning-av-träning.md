---
id: TASK-7
title: Natt-/inaktivitetsschemaläggning av träning
status: To Do
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - träning
  - schema
  - speckrav
dependencies: []
references:
  - trainer
  - training-view
priority: medium
type: feature
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
specs.md kräver "träning endast nattetid eller under inaktivitet" - det är bara antigravity som implementerat detta: en TrainingScheduler (QObject + QTimer) med köade jobb, nattfönster (23:00-05:00) och inaktivitetsdetektering via ett globalt QEvent-filter på QApplication (mus/tangentbord). Se jämförelse_argon.md avsnitt 5:3.

Portera konceptet: i träningsvyn en ruta "Kör: direkt / natte (23-05) / vid inaktivitet (N min)", scheduler i GUI-processen som startar TrainingWorker när villkoret uppfylls, status i statusraden.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 träning kan köas till ett nattfönster (konfigurerbara tider i inställningar)
- [ ] #2 träning kan köas till efter N minuters inaktivitet (global aktivitetsdetektering)
- [ ] #3 köat jobb visas i statusraden och kan avbokas
<!-- AC:END -->
