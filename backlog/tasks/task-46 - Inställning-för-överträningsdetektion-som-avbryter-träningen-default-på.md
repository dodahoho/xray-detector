---
id: TASK-46
title: >-
  Träning - Inställning för överträningsdetektion som avbryter träningen
  (default på)
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T11:51:00Z'
updated_date: '2026-11-12T09:53:00Z'
labels: []
dependencies:
  - TASK-44
references:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/settings_view.py
modified_files:
  - README.md
  - xray_detector/domain/training.py
  - xray_detector/infrastructure/training/epoch_metrics.py
  - xray_detector/infrastructure/training/overfitting.py
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/ui/training_view.py
  - tests/test_overfitting.py
  - tests/test_log_layout.py
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. OverfittingGuard i infrastructure/training/overfitting.py: larmar när valvärdet (mAP50-95, annars mAP50, annars -val-loss) stått still i patience epoker medan train-loss fortsätter sjunka.
2. Träningsprocessen matar vakten från epokrapportören och skickar ABORT {json} med orsaken. YOLO stoppas i on_fit_epoch_end (trainer.stop) och får patience som reserv; RF-DETR använder paketets early_stopping med samma patience eftersom det saknar publik callback-krok.
3. Manifestet skrivs med status aborted och abort_reason, så bästa vikter och manifest finns kvar.
4. Träningsvyn får kryssrutan Avbryt vid överträning, på som default, sparad i settings.ini och skickad som --overfitting-guard.
5. GUI:t visar orsaken i epoketiketten och statusraden via signalen abort_reason.
6. Tester med syntetiska kurvor som ska respektive inte ska utlösa avbrott.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Vakten jämför valvärdet (mAP50-95, annars mAP50, annars val-loss) med train-loss och larmar först när valvärdet stått still i patience epoker och train-loss samtidigt sjunkit. Avbrottet sker i träningsprocessen: YOLO sätter trainer.stop i on_fit_epoch_end och får samma patience som reserv i ultralytics early stopping; RF-DETR använder paketets early_stopping med samma patience eftersom TrainConfig saknar fält för egna callbacks. Verifierat med riktiga CPU-körningar: med vakten på avbröts en 6-epokskörning efter 5 epoker, ABORT-raden skrevs med orsaken och manifestet fick status aborted med abort_reason; med vakten av gick en 4-epokskörning alla epoker och manifestet fick status completed. RF-DETR-grenen är bara täckt av enhetstester: pytorch_lightning saknas i miljön så rfdetr.train() kan inte köras här.
<!-- SECTION:NOTES:END -->
