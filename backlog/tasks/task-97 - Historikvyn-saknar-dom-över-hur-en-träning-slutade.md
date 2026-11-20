---
id: TASK-97
title: Historikvyn saknar dom över hur en träning slutade
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:27:00Z'
updated_date: '2026-11-16T19:18:00Z'
labels: []
dependencies: []
priority: medium
type: enhancement
ordinal: 373000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-89. `OverfittingGuard` avbryter en träning som övertränar, men ingenstans står det efteråt vad körningen led av. Historikvyn visar mAP, epoker och status, men inte om kurvan planade ut, om modellen övertränade eller om träningen helt enkelt var för kort — vilket är precis det man behöver veta för att välja nästa steg. xray_modeltrainer har `OverfitMonitor.verdict()` som klassar körningen som still improving, overfitting eller plateaued med ett konkret råd, och `diagnose.py` som skriver ut domen ur en sparad trace. Här finns redan epokhistoriken via `run_epochs()`, så domen kan räknas fram ur samma data. Notera också att en körning som vakten stoppar får status aborted, trots att ett stopp för överträning är ett lyckat utfall.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Historikvyn visar en dom för en avslutad körning: fortsätter förbättras, övertränad eller avstannad
- [x] #2 Domen bygger på körningens sparade epokvärden
- [x] #3 En körning som stoppats av överträningsvakten går att skilja från en som kraschade
- [x] #4 Test täcker de tre domslagen på kända epokserier
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
1. Dom-funktion som klassar en epokserie som fortsätter förbättras, övertränad eller avstannad, med ett konkret råd.
2. TrainingRun.verdict räknar fram domen ur körningens sparade epokvärden.
3. Manifestet får stop_reason så ett stopp av överträningsvakten går att skilja från en krasch.
4. Historikvyn visar domen som kolumn och i detaljraden.
5. Test för de tre domslagen på kända epokserier.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat:
- infrastructure/training/verdict.py: verdict() klassar en epokserie som improving/overfitting/plateaued/unknown med ett konkret råd. Kräver minst fem epoker; en kurva som planar ut har sin bästa epok sist, så det krävs också en mätbar vinst (> 0.005) över det sista fönstret för att räknas som förbättring. Överträning kräver att train-loss föll medan val-loss steg efter bästa epoken.
- application/training_history.py: TrainingRun.verdict räknar fram domen ur körningens sparade epokvärden (run_epochs), stop_reason läses ur manifestet och status_label skiljer 'Avbruten (överträning)' från 'Avbruten (fel)'.
- train_task.py: _RunState.stop_reason sätts till 'overfitting' när vakten stoppade körningen och 'error' vid ett undantag, via _finish_state(); manifestet skriver fältet.
- ui/training_history.py: Dom-kolumn i tabellen och domen i detaljraden.

Verifiering: tests/test_training_verdict.py (14 tester) täcker de tre domslagen på kända epokserier, att för få epoker ger '-', att mAP50 används när mAP50-95 saknas, att domen räknas ur sparade epokvärden, att vakten och kraschen får olika etikett, att _finish_state sätter rätt stop_reason och att historikvyn visar domen. Hela sviten: 747 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Historikvyn visar nu en dom över hur en träning slutade. Domen räknas fram ur körningens sparade epokvärden och klassar körningen som Förbättras, Övertränad eller Avstannad med ett konkret råd. En kurva som planar ut har sin bästa epok sist, så det krävs både att bästa epoken ligger inom det sista fönstret och en mätbar mAP-vinst över fönstret för att räknas som förbättring; överträning kräver att train-loss föll medan val-loss steg efter den bästa epoken. Färre än fem epoker går inte att bedöma och ger '-'. Domen syns som en egen kolumn och i detaljraden.

Manifestet får också stop_reason: 'overfitting' när överträningsvakten stoppade körningen och 'error' vid ett undantag, så historikvyn kan visa 'Avbruten (överträning)' respektive 'Avbruten (fel)'. Ett stopp av vakten är ett lyckat utfall och går därför inte längre att förväxla med en krasch.

Verifiering: tests/test_training_verdict.py (14 tester) täcker de tre domslagen på kända epokserier, att för få epoker ger '-', att mAP50 används när mAP50-95 saknas, att domen räknas ur sparade epokvärden, att vakten och kraschen får olika etikett, att _finish_state sätter rätt stop_reason och att historikvyn visar domen. Hela sviten: 747 passed, 1 skipped.

Begränsning: domen kräver att metrics-filen finns kvar i körningskatalogen; äldre körningar utan den visar '-'.
<!-- SECTION:FINAL_SUMMARY:END -->
