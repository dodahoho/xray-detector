---
id: TASK-7
title: Natt-/inaktivitetsschemaläggning av träning
status: Done
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T12:53:00Z'
labels:
  - träning
  - schema
  - speckrav
dependencies: []
references:
  - trainer
  - training-view
modified_files:
  - xray_detector/application/training_service.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/settings_view.py
  - tests/test_training_scheduler.py
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
- [x] #1 träning kan köas till ett nattfönster (konfigurerbara tider i inställningar)
- [x] #2 träning kan köas till efter N minuters inaktivitet (global aktivitetsdetektering)
- [x] #3 köat jobb visas i statusraden och kan avbokas
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TrainingScheduler i application-lagret kvar träningsjobb med QTimer-pollning (5 s): natte-lage startar jobbet endast inne i konfigurerbart nattfönster (default 23:00-05:00, hanterar midnattsomslag), inaktivitetslage startar efter N minuter (default 30) without mus-/tangentaktivitet - ett globalt QEvent-filter pa QApplication rapporterar aktiviteten. Tranningsvyn far 'Kor:'-komb (Direkt/Nattetid/Efter inaktivitet): direkt startar worker via TrainingService.worker_created; schemalagda jobb kvas med statusmeddelande i statusraden ('Traning koad till nattfönstret 23:00-05:00' resp '...vid inaktivitet (30 min)') och 'Avbryt' knappen avbokar koat jobb alternativt avbryter paagande transprocess. Installningsfliken far en 'Traningsschema'-ruta dar nattfönstrets start/slut-timme och inaktivitetsgransen satts och persistas i QSettings (training/night_start_hour osv.). Verifierat: 7 nya tester (midnattsomslagLogik, start inne/ute fönstret, inaktivitet vanta+start, statusmeddelanden, ko-flode via riktig MainWindow med avbokning); hel svit 73 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
