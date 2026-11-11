---
id: TASK-46
title: Inställning för överträningsdetektion som avbryter träningen (default på)
status: To Do
assignee: []
created_date: '2026-11-11T11:51:00Z'
labels: []
dependencies:
  - TASK-44
references:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/settings_view.py
priority: high
type: feature
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Det finns i dag ingen överträningsdetektion. Ultralytics patience är 100 som default och sätts inte av appen, så en körning på 100 epoker stoppar i praktiken aldrig i förtid. RF-DETR har early_stopping men den är False som default och sätts inte heller. Ingen av dem mäter överträning, det vill säga att train-loss fortsätter ner medan val-mAP vänder ner; ultralytics patience mäter bara utebliven förbättring av fitness.

Kravet är en inställning i träningsvyn, aktiverad som default, som detekterar överträning och avbryter träningen. Avbrottet ska ske i träningsprocessen så att bästa vikter och manifest hinner sparas (se TASK-47), inte genom att GUI:t dödar processen. Detektionen behöver epokvisa train- och valvärden (TASK-44). Inställningen ska följa med till träningsprocessen som argument och bevaras mellan starter.

Att ta ställning till: tröskel och patience för detektionen, om den ska vara konfigurerbar eller bara av/på, och hur avbrottsorsaken rapporteras till GUI:t. RF-DETR saknar publik callback-krok i installerad version (self.callbacks är oanvänd), så detektionen kan behöva byggas på metrics.csv eller på inbyggd early stopping; utred och välj.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Träningsvyn har en inställning för överträningsdetektion som är aktiverad som default
- [ ] #2 Inställningen sparas och återställs mellan starter
- [ ] #3 Inställningen skickas till träningsprocessen
- [ ] #4 Träningen avbryts när överträning detekteras
- [ ] #5 Avbrottet sker i träningsprocessen så att bästa vikter och manifest sparas
- [ ] #6 GUI:t visar varför träningen avbröts
- [ ] #7 Detektionen fungerar för YOLO
- [ ] #8 Detektionen fungerar för RF-DETR
- [ ] #9 Avstängd inställning ger ingen automatisk avbrytning
- [ ] #10 Tester täcker en syntetisk kurva som ska respektive inte ska utlösa avbrott
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->
